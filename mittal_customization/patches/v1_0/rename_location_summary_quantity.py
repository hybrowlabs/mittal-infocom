# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

import frappe

OLD = "Location Summary (Quantity)"


def execute():
	"""Drop the report that was first shipped under a bracketed name.

	Frappe builds the path to a script report's module from the report name, and the
	brackets survive frappe.scrub, so "Location Summary (Quantity)" looked for a module
	called location_summary_(quantity) and the report could not run at all. It is now
	called Location Summary Quantity. The record left behind by the earlier migrate
	would otherwise stay in the report list and keep raising ModuleNotFoundError.
	"""
	if frappe.db.exists("Report", OLD):
		frappe.delete_doc("Report", OLD, ignore_permissions=True, force=True)
