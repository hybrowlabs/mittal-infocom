# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.report.stock_balance.stock_balance import StockBalanceReport
from frappe import _
from frappe.utils import cint, flt, formatdate, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.company:
		frappe.throw(_("Company is mandatory"))

	if not filters.to_date:
		filters.to_date = today()

	if not filters.from_date:
		filters.from_date = get_default_from_date(filters)

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after As On Date"))

	warehouses = get_warehouses(filters)
	columns = get_columns(filters, warehouses)
	message = get_period_message(filters)

	if not warehouses:
		return columns, [], message

	balances = get_stock_balances(filters, warehouses)

	return columns, get_data(filters, warehouses, balances), message


def get_default_from_date(filters):
	"""Start of the fiscal year the As On Date falls in."""
	from erpnext.accounts.utils import get_fiscal_year

	try:
		return get_fiscal_year(filters.to_date, company=filters.company)[1]
	except Exception:
		return filters.to_date


def get_period_message(filters):
	"""Shown above the report, and used as the period line in the Tally-format export.

	The figures are a closing balance and so depend only on the As On Date. From Date
	sets the period the statement is presented for, the same way Tally does.
	"""
	return _("Closing balance as on <b>{0}</b> &nbsp;|&nbsp; Period: {1} to {2}").format(
		formatdate(filters.to_date, "dd-MM-yyyy"),
		formatdate(filters.from_date, "dd-MM-yyyy"),
		formatdate(filters.to_date, "dd-MM-yyyy"),
	)


def get_warehouses(filters):
	conditions = {"company": filters.company, "is_group": 0, "disabled": 0}

	if filters.warehouse:
		conditions["name"] = ("in", filters.warehouse)

	warehouses = frappe.get_all(
		"Warehouse", filters=conditions, fields=["name", "warehouse_name"], order_by="name"
	)

	# a few warehouse names carry the company abbreviation and most do not -- strip it so
	# the column headings read consistently
	abbr = frappe.db.get_value("Company", filters.company, "abbr")
	suffix = f" - {abbr}" if abbr else ""

	for warehouse in warehouses:
		label = warehouse.warehouse_name or warehouse.name
		if suffix and label.endswith(suffix):
			label = label[: -len(suffix)]
		warehouse.label = label.strip()

	return warehouses


def get_stock_balances(filters, warehouses):
	"""Closing balance per item and warehouse, from the standard Stock Balance report.

	Reusing it keeps this report tied to Stock Balance and inherits its handling of
	Stock Reconciliation entries (which reset the balance instead of adding to it) and
	of Closing Stock Balance snapshots. Only `to_date` bounds the ledger it reads --
	`from_date` merely splits opening from period movement, which this report does not
	show, so it never changes the closing figures.
	"""
	stock_balance_filters = frappe._dict(
		{
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"warehouse": [d.name for d in warehouses],
			"item_group": filters.item_group,
			"include_zero_stock_items": cint(filters.show_zero_stock),
			"ignore_closing_balance": 0,
		}
	)

	_columns, data = StockBalanceReport(stock_balance_filters).run()

	return data


def get_item_groups(filters):
	conditions = {}

	if filters.item_group:
		lft, rgt = frappe.db.get_value("Item Group", filters.item_group, ["lft", "rgt"])
		conditions = {"lft": (">=", lft), "rgt": ("<=", rgt)}

	return frappe.get_all(
		"Item Group",
		filters=conditions,
		fields=["name", "parent_item_group", "lft", "rgt"],
		order_by="lft",
	)


def add_balance(totals, warehouse, qty, value):
	balance = totals.setdefault(warehouse, {"qty": 0.0, "value": 0.0})
	balance["qty"] += flt(qty)
	balance["value"] += flt(value)


def has_balance(totals):
	return any(flt(d.get("qty")) or flt(d.get("value")) for d in totals.values())


def get_data(filters, warehouses, balances):
	item_groups = get_item_groups(filters)

	if not item_groups:
		return []

	group_names = {d.name for d in item_groups}
	show_zero_stock = cint(filters.show_zero_stock)

	item_totals = {}
	item_details = {}

	for row in balances:
		row = frappe._dict(row)

		if row.item_group not in group_names:
			continue

		item_details.setdefault(
			row.item_code, frappe._dict({"item_name": row.item_name, "item_group": row.item_group})
		)
		add_balance(item_totals.setdefault(row.item_code, {}), row.warehouse, row.bal_qty, row.bal_val)

	group_totals = {d.name: {} for d in item_groups}

	for item_code, warehouse_balances in item_totals.items():
		totals = group_totals[item_details[item_code].item_group]
		for warehouse, balance in warehouse_balances.items():
			add_balance(totals, warehouse, balance["qty"], balance["value"])

	# roll child groups into their parent, deepest first (a child always has a higher lft)
	for group in sorted(item_groups, key=lambda d: d.lft, reverse=True):
		parent_totals = group_totals.get(group.parent_item_group)
		if parent_totals is None:
			continue

		for warehouse, balance in group_totals[group.name].items():
			add_balance(parent_totals, warehouse, balance["qty"], balance["value"])

	child_groups = {}
	for group in item_groups:
		child_groups.setdefault(group.parent_item_group, []).append(group)

	group_items = {}
	for item_code in item_totals:
		group_items.setdefault(item_details[item_code].item_group, []).append(item_code)

	data = []

	def add_items(group_name, parent_label, indent):
		for item_code in sorted(
			group_items.get(group_name, []), key=lambda d: item_details[d].item_name or d
		):
			data.append(
				build_row(
					item_details[item_code].item_name or item_code,
					parent_label,
					indent,
					warehouses,
					item_totals[item_code],
					filters,
					item_code=item_code,
				)
			)

	def add_group(group, parent_label, indent):
		totals = group_totals[group.name]

		if not show_zero_stock and not has_balance(totals):
			return

		data.append(build_row(group.name, parent_label, indent, warehouses, totals, filters, is_group_row=1))

		for child in sorted(child_groups.get(group.name, []), key=lambda d: d.name):
			add_group(child, group.name, indent + 1)

		add_items(group.name, group.name, indent + 1)

	# the root of the tree is not shown as a row -- its totals become the Grand Total
	root = min(item_groups, key=lambda d: d.lft)

	for child in sorted(child_groups.get(root.name, []), key=lambda d: d.name):
		add_group(child, None, 0)

	add_items(root.name, None, 0)

	if data:
		data.append(
			build_row(
				_("Grand Total"),
				None,
				0,
				warehouses,
				group_totals[root.name],
				filters,
				is_group_row=1,
				show_rate=False,
			)
		)

	return data


def build_row(
	label,
	parent_label,
	indent,
	warehouses,
	totals,
	filters,
	item_code=None,
	is_group_row=0,
	show_rate=True,
):
	row = {
		"particulars": label,
		"parent_particulars": parent_label,
		"indent": indent,
		"item_code": item_code,
		"is_group_row": is_group_row,
	}

	total_qty = total_value = 0.0

	for warehouse in warehouses:
		key = frappe.scrub(warehouse.name)
		balance = totals.get(warehouse.name) or {}
		qty, value = flt(balance.get("qty")), flt(balance.get("value"))

		total_qty += qty
		total_value += value

		row[f"{key}_qty"] = qty or None
		row[f"{key}_rate"] = (value / qty) if (qty and show_rate) else None
		row[f"{key}_value"] = value or None

	if cint(filters.show_total_column):
		row["total_qty"] = total_qty or None
		row["total_rate"] = (total_value / total_qty) if (total_qty and show_rate) else None
		row["total_value"] = total_value or None

	return row


def get_columns(filters, warehouses):
	columns = [
		{
			"label": _("Particulars"),
			"fieldname": "particulars",
			"fieldtype": "Data",
			"width": 360,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
	]

	for warehouse in warehouses:
		key = frappe.scrub(warehouse.name)
		label = warehouse.label

		columns += [
			{
				"label": _("{0} - Qty").format(label),
				"fieldname": f"{key}_qty",
				"fieldtype": "Int",
				"width": 100,
			},
			{
				"label": _("{0} - Rate").format(label),
				"fieldname": f"{key}_rate",
				"fieldtype": "Currency",
				"width": 110,
			},
			{
				"label": _("{0} - Value").format(label),
				"fieldname": f"{key}_value",
				"fieldtype": "Currency",
				"width": 130,
			},
		]

	if cint(filters.show_total_column):
		columns += [
			{
				"label": _("Total Qty"),
				"fieldname": "total_qty",
				"fieldtype": "Int",
				"width": 100,
			},
			{
				"label": _("Total Rate"),
				"fieldname": "total_rate",
				"fieldtype": "Currency",
				"width": 110,
			},
			{
				"label": _("Total Value"),
				"fieldname": "total_value",
				"fieldtype": "Currency",
				"width": 140,
			},
		]

	return columns
