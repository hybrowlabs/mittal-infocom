# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""The letterhead block Tally prints above every statement."""

import frappe
from frappe import _


def get_company_address(company):
	"""The address to print on the letterhead.

	Prefers the one marked as primary. Companies here have an address per branch and
	none is marked primary, so fall back to the record ERPNext names after the company
	itself, which is the registered office.
	"""
	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company],
			["disabled", "=", 0],
		],
		fields=["name", "is_primary_address"],
		order_by="is_primary_address desc, name",
	)
	if not addresses:
		return None

	for address in addresses:
		if address.is_primary_address:
			return address.name

	for address in addresses:
		if address.name.startswith(company):
			return address.name

	return addresses[0].name


def get_address_lines(company):
	name = get_company_address(company)
	if not name:
		return []

	address = frappe.db.get_value(
		"Address",
		name,
		["address_line1", "address_line2", "city", "state", "pincode", "phone"],
		as_dict=True,
	)
	if not address:
		return []

	lines = [address.address_line1, address.address_line2]

	locality = ", ".join([part for part in [address.city, address.state] if part])
	if address.pincode:
		locality = f"{locality} - {address.pincode}" if locality else address.pincode
	lines.append(locality)

	phone = address.phone or frappe.db.get_value("Company", company, "phone_no")
	if phone:
		lines.append(_("Tel. No - {0}").format(phone))

	return [line.strip() for line in lines if line and line.strip()]
