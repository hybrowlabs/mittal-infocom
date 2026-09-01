# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Builds the Tally Account Group list from the chart of accounts and tags every
ledger with the group it is printed under.

Run it after the chart of accounts changes:

	bench execute mittal_customization.tally.setup.setup_tally_reporting
"""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from mittal_customization.tally.config import (
	BLOCK_OVERRIDES,
	BLOCK_ORDER,
	DISPLAY_LABELS,
	OTHER_BLOCK,
	ROOT_LEVEL_BLOCK,
	SIDE_BY_ROOT_TYPE,
)


def setup_tally_reporting(company=None):
	"""Rebuild the Tally Account Groups from the chart of accounts and tag every ledger.

	Safe to run repeatedly; it is called on every migrate.
	"""
	if not frappe.db.table_exists("Tally Account Group"):
		return

	ensure_custom_fields()
	lines = derive_lines(company)
	sync_tally_account_groups(lines)
	tagged = tag_accounts(lines)
	removed = remove_orphan_groups(lines)

	frappe.db.commit()

	return {"groups": len(lines), "accounts_tagged": tagged, "groups_removed": removed}


def ensure_custom_fields():
	create_custom_field(
		"Account",
		{
			"fieldname": "tally_group",
			"label": "Tally Group",
			"fieldtype": "Link",
			"options": "Tally Account Group",
			"insert_after": "account_type",
			"description": _("Line this ledger is printed under on the Tally format statements."),
		},
		ignore_validate=True,
	)

	# stored, not just displayed, so the statement templates can group on it
	create_custom_field(
		"Account",
		{
			"fieldname": "tally_block",
			"label": "Tally Block",
			"fieldtype": "Data",
			"fetch_from": "tally_group.block",
			"fetch_if_empty": 0,
			"insert_after": "tally_group",
			"read_only": 1,
		},
		ignore_validate=True,
	)


def get_accounts(company=None):
	filters = {"company": company} if company else {}

	return frappe.get_all(
		"Account",
		filters=filters,
		fields=["name", "account_name", "parent_account", "is_group", "root_type"],
	)


def derive_lines(company=None):
	"""Group every balance sheet ledger into the line it is printed under.

	The block is the group directly below the root and the line is the next group
	below it, falling back to the ledger itself when there is none.
	"""
	accounts = get_accounts(company)
	by_name = {d.name: d for d in accounts}

	lines = {}

	for account in accounts:
		if account.is_group or account.root_type not in SIDE_BY_ROOT_TYPE:
			continue

		ancestors = get_ancestors(account, by_name)

		side = SIDE_BY_ROOT_TYPE[account.root_type]
		line = get_line(account, ancestors)
		block = get_block(ancestors, line, side)
		key = (side, block, line)

		lines.setdefault(
			key,
			frappe._dict(
				{
					"side": side,
					"block": block,
					"line": line,
					"label": DISPLAY_LABELS.get(line, line),
					"accounts": [],
				}
			),
		).accounts.append(account.name)

	return sort_lines(lines.values())


def get_ancestors(account, by_name):
	"""Ancestors of an account, outermost first."""
	ancestors = []
	current = account

	while current and current.parent_account:
		current = by_name.get(current.parent_account)
		if current:
			ancestors.append(current)

	ancestors.reverse()

	return ancestors


def clean(name):
	"""Account names in the chart carry the odd trailing space. Frappe strips it when
	it names the group record, so the name has to be stripped here too or the link
	stored on the ledger will not match the record."""
	return (name or "").strip()


def get_line(account, ancestors):
	"""The group a ledger is printed under, one level below its block.

	A group that Tally prints as a block of its own takes the place of the block, so
	its own children become the lines -- that is how Bank OD A/c, Secured Loans and
	Unsecured Loans appear under Loans (Liability).
	"""
	depth = 2

	while len(ancestors) > depth and clean(ancestors[depth].account_name) in BLOCK_OVERRIDES:
		depth += 1

	if len(ancestors) > depth:
		return clean(ancestors[depth].account_name)

	return clean(account.account_name)


def get_block(ancestors, line, side):
	# a group Tally lifts out of the tree becomes the block for everything beneath it
	for ancestor in reversed(ancestors):
		if clean(ancestor.account_name) in BLOCK_OVERRIDES:
			return BLOCK_OVERRIDES[clean(ancestor.account_name)]

	if line in BLOCK_OVERRIDES:
		return BLOCK_OVERRIDES[line]

	if line in ROOT_LEVEL_BLOCK:
		return ROOT_LEVEL_BLOCK[line]

	if len(ancestors) > 1:
		return clean(ancestors[1].account_name)

	# posted straight against the root group, so it has no block of its own
	return OTHER_BLOCK.get(side, line)


def sort_lines(lines):
	def sort_key(line):
		order = BLOCK_ORDER.get(line.side) or []
		block_rank = order.index(line.block) if line.block in order else len(order)

		return (line.side, block_rank, line.block, line.label)

	lines = sorted(lines, key=sort_key)

	for index, line in enumerate(lines, start=1):
		line.display_order = index * 10

	return lines


def sync_tally_account_groups(lines):
	for line in lines:
		values = {
			"display_label": line.label if line.label != line.line else None,
			"side": line.side,
			"block": line.block,
			"display_order": line.display_order,
		}

		if frappe.db.exists("Tally Account Group", line.line):
			group = frappe.get_doc("Tally Account Group", line.line)
			group.update(values)
			group.save(ignore_permissions=True)
			continue

		group = frappe.new_doc("Tally Account Group")
		group.tally_group_name = line.line
		group.update(values)
		group.insert(ignore_permissions=True)


def tag_accounts(lines):
	tagged = 0

	for line in lines:
		values = {"tally_group": line.line, "tally_block": line.block}

		for account in line.accounts:
			current = frappe.db.get_value("Account", account, ["tally_group", "tally_block"], as_dict=True)
			if current and current.tally_group == line.line and current.tally_block == line.block:
				continue

			frappe.db.set_value("Account", account, values, update_modified=False)
			tagged += 1

	return tagged


def remove_orphan_groups(lines):
	"""Drop groups left behind by an earlier chart of accounts."""
	current = {line.line for line in lines}
	removed = 0

	for name in frappe.get_all("Tally Account Group", pluck="name"):
		if name in current:
			continue

		if frappe.db.exists("Account", {"tally_group": name}):
			continue

		frappe.delete_doc("Tally Account Group", name, ignore_permissions=True, force=True)
		removed += 1

	return removed
