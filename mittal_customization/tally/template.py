# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Builds the Tally format Financial Report Templates from the Tally Account Groups.

The templates are ordinary Financial Report Template records once written, so they can
be edited in the desk afterwards. Rebuild them after the chart of accounts changes:

	bench execute mittal_customization.tally.template.build_templates
"""

import frappe
from frappe import _

from mittal_customization.tally.config import BLOCK_ORDER, TRADING_BLOCKS

BALANCE_SHEET_TEMPLATE = "Tally Balance Sheet"
PROFIT_AND_LOSS_TEMPLATE = "Tally Profit & Loss"

CLOSING_BALANCE = "Closing Balance"
# the profit and loss account reports what moved during the period, not a running balance
PERIOD_MOVEMENT = "Period Movement (Debits - Credits)"

SIDE_ROOT_TYPE = {
	"Liabilities": "Liability",
	"Assets": "Asset",
	"Expenses": "Expense",
	"Income": "Income",
}
SIDE_PREFIX = {"Liabilities": "L", "Assets": "A", "Expenses": "E", "Income": "I"}

PROFIT_AND_LOSS_BLOCK = "Profit & Loss A/c"


def build_templates():
	build_balance_sheet_template()
	build_profit_and_loss_template()
	frappe.db.commit()

	return {"templates": [BALANCE_SHEET_TEMPLATE, PROFIT_AND_LOSS_TEMPLATE]}


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

	def account_row(
		self, code, label, formula, indent=0, bold=0, italic=0, reverse=0, balance_type=CLOSING_BALANCE
	):
		return self.add(
			"Account Data",
			reference_code=code,
			display_name=label,
			indentation_level=indent,
			balance_type=balance_type,
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


def build_profit_and_loss_template():
	"""The Tally profit and loss account: a trading half that closes at Gross Profit,
	and a second half below it that closes at Nett Profit.

	The chart of accounts is kept on perpetual inventory, so cost of goods sold is
	posted as it happens and there is no Opening Stock, Purchase Accounts or Closing
	Stock line to print. Those three lines of the Tally statement have no entry in the
	ledger to draw on; the trading account is made up of the direct blocks instead.
	"""
	builder = RowBuilder()
	plan = get_plan(builder)

	trading = {side: [b["code"] for b in blocks if b["trading"]] for side, blocks in plan.items()}
	below = {side: [b["code"] for b in blocks if not b["trading"]] for side, blocks in plan.items()}

	# a row is stored under its reference code with its sign already reversed, so both
	# sides read as positive here and the formulas are plain arithmetic
	gross_profit = "({0}) - ({1})".format(total_of(trading["Income"]), total_of(trading["Expenses"]))
	nett_profit = "E_GROSS_PROFIT + ({0}) - ({1})".format(
		total_of(below["Income"]), total_of(below["Expenses"])
	)

	builder.add("Section Break")

	for side in ("Expenses", "Income"):
		builder.add("Column Break", display_name=_("Particulars"))
		emit_blocks(builder, plan[side], side, trading_half=True)

		if side == "Expenses":
			builder.add(
				"Calculated Amount",
				reference_code="E_GROSS_PROFIT",
				display_name=_("Gross Profit c/o"),
				indentation_level=0,
				calculation_formula=gross_profit,
				fieldtype="Currency",
				bold_text=1,
				italic_text=1,
			)
			subtotal = f"{total_of(trading['Expenses'])} + E_GROSS_PROFIT"
		else:
			subtotal = total_of(trading["Income"])

		builder.blank()
		builder.add(
			"Calculated Amount",
			reference_code=f"{SIDE_PREFIX[side]}_TRADING_TOTAL",
			display_name="",
			indentation_level=0,
			calculation_formula=subtotal,
			fieldtype="Currency",
		)

	builder.add("Section Break")

	for side in ("Expenses", "Income"):
		builder.add("Column Break", display_name=_("Particulars"))

		if side == "Income":
			builder.add(
				"Calculated Amount",
				reference_code="I_GROSS_PROFIT",
				display_name=_("Gross Profit b/f"),
				indentation_level=0,
				calculation_formula="E_GROSS_PROFIT",
				fieldtype="Currency",
				bold_text=1,
				italic_text=1,
			)
			builder.blank()

		emit_blocks(builder, plan[side], side, trading_half=False)

		if side == "Expenses":
			builder.add(
				"Calculated Amount",
				reference_code="E_NETT_PROFIT",
				display_name=_("Nett Profit"),
				indentation_level=0,
				calculation_formula=nett_profit,
				fieldtype="Currency",
				bold_text=1,
				italic_text=1,
			)
			total = f"{total_of(below['Expenses'])} + E_NETT_PROFIT"
		else:
			total = f"E_GROSS_PROFIT + ({total_of(below['Income'])})"

		builder.blank()
		builder.add(
			"Calculated Amount",
			reference_code=f"{SIDE_PREFIX[side]}_TOTAL",
			display_name=_("Total"),
			indentation_level=0,
			calculation_formula=total,
			fieldtype="Currency",
			bold_text=1,
		)

	save_template(PROFIT_AND_LOSS_TEMPLATE, "Profit and Loss Statement", builder.rows)


def get_plan(builder):
	"""Reference codes for every block, worked out before any row is written so that a
	total on one side can refer to a block on the other."""
	plan = {}

	for side in ("Expenses", "Income"):
		plan[side] = [
			{
				"block": block,
				"groups": groups,
				"code": builder.code(f"{SIDE_PREFIX[side]}_BLK", block),
				"trading": block in TRADING_BLOCKS.get(side, ()),
			}
			for block, groups in get_groups(side)
		]

	return plan


def emit_blocks(builder, blocks, side, trading_half):
	root_type = SIDE_ROOT_TYPE[side]
	reverse = 1 if side == "Income" else 0

	for entry in blocks:
		if entry["trading"] != trading_half:
			continue

		builder.account_row(
			entry["code"],
			entry["block"],
			{"and": [["tally_block", "=", entry["block"]], ["root_type", "=", root_type]]},
			indent=0,
			bold=1,
			reverse=reverse,
			balance_type=PERIOD_MOVEMENT,
		)

		for group in entry["groups"]:
			builder.account_row(
				builder.code(SIDE_PREFIX[side], group.name),
				group.display_label or group.name,
				["tally_group", "=", group.name],
				indent=1,
				italic=1,
				reverse=reverse,
				balance_type=PERIOD_MOVEMENT,
			)

		builder.blank()


def total_of(codes):
	return " + ".join(codes) if codes else "0"
