# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Build the Tally Account Groups and the Tally format statement templates.

	Only the first run is automatic. Rebuild after the chart of accounts changes with
	`bench execute mittal_customization.tally.setup.setup_tally_reporting` followed by
	`bench execute mittal_customization.tally.template.build_templates`, so that edits
	made to the templates in the desk are not overwritten by a migrate.
	"""
	if not frappe.db.exists("DocType", "Financial Report Template"):
		# the templates live in the ifrs_reporting app
		return

	from mittal_customization.tally.setup import setup_tally_reporting
	from mittal_customization.tally.template import build_templates

	setup_tally_reporting()
	build_templates()
