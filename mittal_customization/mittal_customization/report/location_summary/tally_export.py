# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Excel export of the Location Summary report in the layout Tally produces.

Reproduces the letterhead block, the merged four row header per location and the
indented item group tree of the Tally "Location Summary" export, so the file can be
circulated in the format the business already reads.
"""

import json
from io import BytesIO

import frappe
import openpyxl
from frappe import _
from frappe.utils import cint, formatdate
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

from mittal_customization.tally.letterhead import get_address_lines

from mittal_customization.mittal_customization.report.location_summary.location_summary import (
	execute,
	get_warehouses,
)

QTY_FORMAT = '0" no"'
AMOUNT_FORMAT = "0.00"

PARTICULARS_WIDTH = 89.2

# Tally's own widths are too narrow for figures of this size, so each column is sized
# from the values it actually holds, within these bounds
MIN_QTY_WIDTH = 9
MIN_RATE_WIDTH = 12
MIN_VALUE_WIDTH = 14
MAX_COLUMN_WIDTH = 22
WIDTH_PADDING = 2

THIN_BOTTOM = Border(bottom=Side(style="thin"))


def round_value(value):
	return round(value, 2) if value is not None else None


@frappe.whitelist()
def download_tally_format(filters):
	if isinstance(filters, str):
		filters = json.loads(filters)

	filters = frappe._dict(filters)
	frappe.has_permission("Stock Ledger Entry", throw=True)

	_columns, data, _message = execute(filters)

	if not data:
		frappe.throw(_("No stock to report for the selected filters"))

	warehouses = get_warehouses(filters)
	workbook = build_workbook(filters, warehouses, data)

	stream = BytesIO()
	workbook.save(stream)

	frappe.response["filename"] = get_file_name(filters)
	frappe.response["filecontent"] = stream.getvalue()
	frappe.response["type"] = "binary"


def get_file_name(filters):
	return "Location Summary {}.xlsx".format(formatdate(filters.to_date, "dd-MM-yyyy"))


def get_column_groups(filters, warehouses):
	"""One Quantity / Rate / Value triple per location, plus the total if it is shown."""
	groups = []

	for warehouse in warehouses:
		key = frappe.scrub(warehouse.name)
		groups.append((warehouse.label, f"{key}_qty", f"{key}_rate", f"{key}_value"))

	if cint(filters.show_total_column):
		groups.append((_("Total"), "total_qty", "total_rate", "total_value"))

	return groups


def build_workbook(filters, warehouses, data):
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = "Location Summary"

	groups = get_column_groups(filters, warehouses)

	set_column_widths(sheet, groups, data)
	row = write_letterhead(sheet, filters, groups)
	row = write_header(sheet, filters, groups, row)
	write_rows(sheet, groups, data, row)

	sheet.freeze_panes = sheet.cell(row=row, column=2).coordinate

	return workbook


def set_column_widths(sheet, groups, data):
	sheet.column_dimensions["A"].width = PARTICULARS_WIDTH

	column = 2
	for _label, qty_field, rate_field, value_field in groups:
		widths = (
			measure_width(data, qty_field, format_qty, MIN_QTY_WIDTH),
			measure_width(data, rate_field, format_amount, MIN_RATE_WIDTH),
			measure_width(data, value_field, format_amount, MIN_VALUE_WIDTH),
		)
		for width in widths:
			sheet.column_dimensions[get_column_letter(column)].width = width
			column += 1


def format_qty(value):
	return f"{round(value):d} no"


def format_amount(value):
	return f"{value:.2f}"


def measure_width(data, fieldname, formatter, minimum):
	"""Width of the widest figure the column has to show, as Excel renders it."""
	longest = 0

	for row in data:
		value = row.get(fieldname)
		if value is None:
			continue
		longest = max(longest, len(formatter(value)))

	return min(max(longest + WIDTH_PADDING, minimum), MAX_COLUMN_WIDTH)


def write_letterhead(sheet, filters, groups):
	"""Company name, address and phone, then the report title and period."""
	last_column = 1 + len(groups) * 3
	lines = [filters.company, *get_address_lines(filters.company)]
	lines.append(_("Location Summary"))
	lines.append(get_period_label(filters))

	for index, line in enumerate(lines):
		row = index + 1
		cell = sheet.cell(row=row, column=1, value=line)
		cell.font = Font(bold=(index == 0))
		cell.alignment = Alignment(horizontal="left")
		if last_column > 1:
			sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_column)

	return len(lines) + 1


def get_company_caption(filters):
	"""Company name followed by the fiscal year, e.g. "Acme Ltd 26-27"."""
	from erpnext.accounts.utils import get_fiscal_year

	try:
		fiscal_year = get_fiscal_year(filters.to_date, company=filters.company)[0]
	except Exception:
		return filters.company

	return f"{filters.company} {fiscal_year}"


def get_period_label(filters):
	return "{} to {}".format(
		formatdate(filters.from_date, "d-MMM-yy"), formatdate(filters.to_date, "d-MMM-yy")
	)


def write_header(sheet, filters, groups, start_row):
	"""The four merged rows above the Quantity / Rate / Value columns, per location."""
	period = get_period_label(filters)
	captions = [
		[group[0] for group in groups],
		[get_company_caption(filters) for _group in groups],
		[period for _group in groups],
		[_("Closing Balance") for _group in groups],
	]

	for offset, values in enumerate(captions):
		row = start_row + offset
		column = 2
		for value in values:
			cell = sheet.cell(row=row, column=column, value=value)
			cell.font = Font(bold=(offset == 0))
			cell.alignment = Alignment(horizontal="center")
			sheet.merge_cells(start_row=row, start_column=column, end_row=row, end_column=column + 2)
			column += 3

	# "Particulars" sits against the period row, as Tally places it
	particulars = sheet.cell(row=start_row + 2, column=1, value=_("Particulars"))
	particulars.font = Font(bold=True)

	label_row = start_row + 4
	column = 2
	for _group in groups:
		for label in (_("Quantity"), _("Rate"), _("Value")):
			cell = sheet.cell(row=label_row, column=column, value=label)
			cell.font = Font(bold=True)
			cell.alignment = Alignment(horizontal="center")
			cell.border = THIN_BOTTOM
			column += 1

	sheet.cell(row=label_row, column=1).border = THIN_BOTTOM

	return label_row + 1


def write_rows(sheet, groups, data, start_row):
	for offset, source in enumerate(data):
		row = start_row + offset
		is_group = bool(source.get("is_group_row"))

		label = sheet.cell(row=row, column=1, value=source.get("particulars"))
		label.font = Font(bold=is_group)
		# Tally indents each level by two
		label.alignment = Alignment(horizontal="left", indent=(source.get("indent") or 0) * 2)
		if is_group:
			label.border = THIN_BOTTOM

		column = 2
		for _label, qty_field, rate_field, value_field in groups:
			for fieldname, number_format, bold in (
				(qty_field, QTY_FORMAT, is_group),
				(rate_field, AMOUNT_FORMAT, False),
				(value_field, AMOUNT_FORMAT, is_group),
			):
				cell = sheet.cell(row=row, column=column, value=round_value(source.get(fieldname)))
				cell.number_format = number_format
				cell.font = Font(bold=bold)
				cell.alignment = Alignment(horizontal="right")
				if is_group:
					cell.border = THIN_BOTTOM
				column += 1
