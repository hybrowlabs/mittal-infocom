# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Prints a Tally format financial statement as a PDF.

Frappe v15 cannot attach a print format to a report, so the statement is rendered
from the report output here: the letterhead block, the two facing panels, the
Carried Over / Brought Forward lines Tally puts at a page break, and the closing
Total rule.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate
from frappe.utils.pdf import get_pdf

from mittal_customization.tally.letterhead import get_address_lines

TEMPLATE = "mittal_customization/templates/print/tally_statement.html"

# A page is filled by rendered lines rather than by rows, because a long ledger name
# wraps onto a second line and would otherwise push the page over and let the PDF
# engine break it again in the wrong place. The first page carries the address block
# so it holds fewer.
LINES_FIRST_PAGE = 34
LINES_PER_PAGE = 44

# A name too long for the particulars column is set in a smaller size rather than
# wrapped, the way Tally does it, so every row is one line and a page holds a known
# number of them. Widths are measured in units of an average lower case character,
# because a name in capitals takes noticeably more room than its length suggests.
SQUEEZE_WIDTHS = ((24.0, ""), (28.5, "small"), (34.0, "smaller"))
INDENT_WIDTH = 2.4

NARROW_CHARACTERS = set("iljtfr.,;:'`!|()[]{} ")
WIDE_CHARACTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&%@#/")

# Tally's own wording for each statement
STATEMENT_TITLES = {
	"Balance Sheet": "Balance Sheet",
	"Profit and Loss Statement": "Profit & Loss A/c",
}

REPORT_BY_TYPE = {
	"Balance Sheet": "ifrs_reporting.ifrs_reporting.report.balance_sheet.balance_sheet",
	"Profit and Loss Statement": "ifrs_reporting.ifrs_reporting.report.profit_and_loss_statement.profit_and_loss_statement",
}


@frappe.whitelist()
def download_statement_pdf(filters):
	filters = parse_filters(filters)
	statement = build_statement(filters)
	html = frappe.render_template(TEMPLATE, statement)

	frappe.local.response.filename = "{} {}.pdf".format(
		statement["title"], statement["period"]
	).replace("/", "-")
	frappe.local.response.filecontent = get_pdf(
		html,
		{
			"page-size": "A4",
			"orientation": "Portrait",
			"margin-top": "10mm",
			"margin-bottom": "10mm",
			"margin-left": "8mm",
			"margin-right": "8mm",
		},
	)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def preview_statement_html(filters):
	"""The same layout as the PDF, for checking it in the browser."""
	return frappe.render_template(TEMPLATE, build_statement(parse_filters(filters)))


def parse_filters(filters):
	if isinstance(filters, str):
		filters = json.loads(filters)

	filters = frappe._dict(filters or {})

	if not filters.report_template:
		frappe.throw(_("Select a Report Template to print in the Tally format."))

	if not filters.company:
		frappe.throw(_("Company is mandatory"))

	return filters


def build_statement(filters):
	report_type = frappe.db.get_value("Financial Report Template", filters.report_template, "report_type")

	# only the balance sheet carries a running total over a page break; the profit and
	# loss account prints its own Gross Profit, Nett Profit and Total lines instead
	carry = report_type == "Balance Sheet"

	panels, period_key = run_report(filters, report_type, carry)

	left, right = panels
	pages = paginate(left, right, carry)

	return {
		"title": STATEMENT_TITLES.get(report_type, report_type),
		"company": filters.company,
		"address_lines": get_address_lines(filters.company),
		"period": get_period_label(filters),
		# the balance sheet is a position on a date, the profit and loss a period
		"column_head": _("as at {0}").format(formatdate(filters.period_end_date, "d-MMM-yy"))
		if carry
		else get_period_label(filters),
		"headings": get_panel_headings(report_type),
		"pages": pages,
		"period_key": period_key,
		"carry": carry,
		"fmt": format_amount,
	}


def get_panel_headings(report_type):
	if report_type == "Profit and Loss Statement":
		return (_("Particulars"), _("Particulars"))

	return (_("Liabilities"), _("Assets"))


def run_report(filters, report_type, drop_totals):
	module = REPORT_BY_TYPE.get(report_type)
	if not module:
		frappe.throw(_("{0} cannot be printed in the Tally format.").format(report_type))

	execute = frappe.get_attr(f"{module}.execute")
	columns, data = execute(frappe._dict(filters))[:2]

	period_key = get_period_key(columns)
	panels = [extract_panel(data, segment, period_key, drop_totals) for segment in ("seg_0", "seg_1")]

	return panels, period_key


def get_period_key(columns):
	"""The single amount column each panel carries."""
	for column in columns:
		fieldname = column.get("fieldname") or ""
		if fieldname.startswith("seg_0_") and column.get("fieldtype") in ("Currency", "Float"):
			return fieldname[len("seg_0_") :]

	frappe.throw(_("The report returned no amount column to print."))


def extract_panel(data, segment, period_key, drop_totals):
	rows = []

	for row in data:
		values = (row.get("segment_values") or {}).get(segment) or {}
		label = values.get("account_name") or values.get("account") or ""
		amount = row.get(f"{segment}_{period_key}")

		if values.get("is_blank_line") and not label:
			rows.append(blank_row())
			continue

		if not label and amount in (None, ""):
			rows.append(blank_row())
			continue

		indent = cint(values.get("indent"))

		# rows built from an account filter are the real figures; a row at the top level
		# without one is a grand total the template computed. The balance sheet prints
		# its own Total at the foot of the last page, so those are dropped there.
		from_accounts = bool(values.get("account_filters"))
		if drop_totals and indent == 0 and not from_accounts and amount not in (None, ""):
			continue

		rows.append(
			{
				"label": label,
				"amount": flt(amount) if amount not in (None, "") else None,
				"indent": indent,
				"bold": 1 if values.get("bold") else 0,
				"italic": 1 if values.get("italic") else 0,
				"blank": 0,
				"is_block": 1 if indent == 0 else 0,
				"squeeze": get_squeeze(label, indent),
				"amount_squeeze": "small" if amount_width(amount) > 18 else "",
				# Tally rules off above a carried subtotal and above the closing total
				"rule": 1 if indent == 0 and not from_accounts and label in ("", _("Total")) else 0,
			}
		)

	return trim(rows)


def get_squeeze(label, indent):
	"""How much to shrink a name that will not fit the column at full size."""
	width = text_width(label) + indent * INDENT_WIDTH

	for limit, css_class in SQUEEZE_WIDTHS:
		if width <= limit:
			return css_class

	return "tiny"


def amount_width(value):
	return len(format_amount(value))


def text_width(label):
	width = 0.0

	for character in label:
		if character in NARROW_CHARACTERS:
			width += 0.45
		elif character in WIDE_CHARACTERS:
			width += 1.15
		else:
			width += 0.92

	return width


def blank_row():
	return {
		"label": "",
		"amount": None,
		"indent": 0,
		"bold": 0,
		"italic": 0,
		"blank": 1,
		"is_block": 0,
		"squeeze": "",
		"amount_squeeze": "",
		"rule": 0,
	}


def trim(rows):
	while rows and rows[-1]["blank"]:
		rows.pop()

	return rows


def paginate(left, right, carry=True):
	"""Split the panels across pages, carrying the running total over each break.

	Only the block headings count towards the running total; the lines under them are
	already part of their block.
	"""
	pages = []
	total_rows = max(len(left), len(right))
	carried = [0.0, 0.0]
	start = 0
	page_index = 0

	while start < total_rows or not pages:
		budget = LINES_FIRST_PAGE if page_index == 0 else LINES_PER_PAGE
		end = fill_page(left, right, start, total_rows, budget)

		page = {
			"index": page_index,
			"first": page_index == 0,
			"brought_forward": list(carried) if carry and page_index else None,
			"rows": build_page_rows(left, right, start, end),
		}

		for side, rows in enumerate((left, right)):
			for row in rows[start:end]:
				if row["is_block"] and row["amount"] is not None:
					carried[side] += row["amount"]

		page["last"] = end >= total_rows
		page["totals"] = list(carried) if carry else None
		pages.append(page)

		start = end
		page_index += 1

	return pages


def fill_page(left, right, start, total_rows, budget):
	"""Index to stop at so the page holds no more than `budget` rendered lines."""
	used = 0
	index = start

	while index < total_rows:
		lines = max(
			row_lines(left[index] if index < len(left) else None),
			row_lines(right[index] if index < len(right) else None),
		)

		if used + lines > budget and index > start:
			break

		used += lines
		index += 1

	return index


def row_lines(row):
	# names are shrunk rather than wrapped, so every row occupies exactly one line
	return 1


def build_page_rows(left, right, start, end):
	rows = []

	for index in range(start, end):
		rows.append(
			{
				"left": left[index] if index < len(left) else None,
				"right": right[index] if index < len(right) else None,
			}
		)

	return rows


def get_period_label(filters):
	return "{} to {}".format(
		formatdate(filters.period_start_date, "d-MMM-yy"),
		formatdate(filters.period_end_date, "d-MMM-yy"),
	)


def format_amount(value):
	"""Indian digit grouping, with Tally's bracketed minus."""
	if value is None or value == "":
		return ""

	value = flt(value, 2)
	if not value:
		return ""

	negative = value < 0
	whole, _sep, fraction = f"{abs(value):.2f}".partition(".")

	if len(whole) > 3:
		head, tail = whole[:-3], whole[-3:]
		groups = []
		while len(head) > 2:
			groups.insert(0, head[-2:])
			head = head[:-2]
		if head:
			groups.insert(0, head)
		whole = ",".join([*groups, tail])

	formatted = f"{whole}.{fraction}"

	return f"(-){formatted}" if negative else formatted
