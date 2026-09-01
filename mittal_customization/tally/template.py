# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Builds the Tally format Financial Report Templates from the Tally Account Groups.

The templates are ordinary Financial Report Template records once written, so they can
be edited in the desk afterwards. Rebuild them after the chart of accounts changes:

	bench execute mittal_customization.tally.template.build_templates
"""

import frappe

from mittal_customization.tally.config import BLOCK_ORDER

BALANCE_SHEET_TEMPLATE = "Tally Balance Sheet"

SIDE_ROOT_TYPE = {"Liabilities": "Liability", "Assets": "Asset"}
SIDE_PREFIX = {"Liabilities": "L", "Assets": "A"}

PROFIT_AND_LOSS_BLOCK = "Profit & Loss A/c"


def build_templates():
	build_balance_sheet_template()
	frappe.db.commit()

	return {"templates": [BALANCE_SHEET_TEMPLATE]}


def get_groups(side):
	groups = frappe.get_all(
		"Tally Account Group",
		filters={"side": side},
		fields=["name", "display_label", "block", "display_order"],
		order_by="display_order asc",
	)

	blocks = {}
	for group in groups:
		blocks.setdefault(group.block, []).append(group)

	order = BLOCK_ORDER.get(side) or []

	def block_key(block):
		return (order.index(block) if block in order else len(order), block)

	return [(block, blocks[block]) for block in sorted(blocks, key=block_key)]


class RowBuilder:
	def __init__(self):
		self.rows = []
		self.used_codes = set()

	def code(self, prefix, name):
		base = f"{prefix}_{frappe.scrub(name)}".upper()
		base = "".join(c if c.isalnum() or c == "_" else "_" for c in base)[:60]

		code = base
		suffix = 2
		while code in self.used_codes:
			code = f"{base}_{suffix}"
			suffix += 1

		self.used_codes.add(code)

		return code

	def add(self, data_source, **kwargs):
		row = {"data_source": data_source}
		row.update(kwargs)
		self.rows.append(row)

		return row

	def account_row(self, code, label, formula, indent=0, bold=0, italic=0, reverse=0):
		return self.add(
			"Account Data",
			reference_code=code,
			display_name=label,
			indentation_level=indent,
			balance_type="Closing Balance",
			calculation_formula=frappe.as_json(formula),
			fieldtype="Currency",
			bold_text=bold,
			italic_text=italic,
			reverse_sign=reverse,
			hide_when_empty=1,
		)

	def blank(self):
		return self.add("Blank Line")


def build_balance_sheet_template():
	builder = RowBuilder()
	totals = {}

	builder.add("Section Break")

	for side in ("Liabilities", "Assets"):
		builder.add("Column Break", display_name=side)
		totals[side] = build_side(builder, side)

	builder.add("Section Break")

	for side in ("Liabilities", "Assets"):
		if side == "Assets":
			builder.add("Column Break")

		builder.blank()
		builder.add(
			"Calculated Amount",
			reference_code=f"{SIDE_PREFIX[side]}_TOTAL",
			display_name="Total",
			indentation_level=0,
			calculation_formula=" + ".join(totals[side]) or "0",
			fieldtype="Currency",
			bold_text=1,
		)

	save_template(BALANCE_SHEET_TEMPLATE, "Balance Sheet", builder.rows)


def build_side(builder, side):
	"""Emit one panel and return the reference codes that make up its total."""
	prefix = SIDE_PREFIX[side]
	root_type = SIDE_ROOT_TYPE[side]
	reverse = 1 if side == "Liabilities" else 0
	block_codes = []

	for block, groups in get_groups(side):
		if block == PROFIT_AND_LOSS_BLOCK:
			continue

		block_code = builder.code(f"{prefix}_BLK", block)
		block_codes.append(block_code)

		builder.account_row(
			block_code,
			block,
			{"and": [["tally_block", "=", block], ["root_type", "=", root_type]]},
			indent=0,
			bold=1,
			reverse=reverse,
		)

		for group in groups:
			builder.account_row(
				builder.code(prefix, group.name),
				group.display_label or group.name,
				["tally_group", "=", group.name],
				indent=1,
				italic=1,
				reverse=reverse,
			)

		builder.blank()

	if side == "Liabilities":
		block_codes.append(build_profit_and_loss_block(builder))

	return block_codes


def build_profit_and_loss_block(builder):
	"""Tally shows the brought forward balance and the current period side by side."""
	builder.account_row(
		"L_BLK_PROFIT_AND_LOSS",
		PROFIT_AND_LOSS_BLOCK,
		{
			"or": [
				["tally_block", "=", PROFIT_AND_LOSS_BLOCK],
				["root_type", "in", ["Income", "Expense"]],
			]
		},
		indent=0,
		bold=1,
		reverse=1,
	)

	builder.account_row(
		"L_PL_OPENING",
		"Opening Balance",
		["tally_block", "=", PROFIT_AND_LOSS_BLOCK],
		indent=1,
		italic=1,
		reverse=1,
	)

	builder.account_row(
		"L_PL_CURRENT",
		"Current Period",
		["root_type", "in", ["Income", "Expense"]],
		indent=1,
		italic=1,
		reverse=1,
	)

	builder.blank()

	return "L_BLK_PROFIT_AND_LOSS"


def save_template(name, report_type, rows):
	if frappe.db.exists("Financial Report Template", name):
		template = frappe.get_doc("Financial Report Template", name)
		template.rows = []
	else:
		template = frappe.new_doc("Financial Report Template")
		template.template_name = name

	template.report_type = report_type
	template.module = "Mittal Customization"
	template.disabled = 0

	for row in rows:
		template.append("rows", row)

	template.save(ignore_permissions=True)

	return template
