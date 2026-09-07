// Copyright (c) 2026, SAW India and contributors
// For license information, please see license.txt

// Settings are shared with Location Summary; see
// mittal_customization/public/js/location_summary_report.js
frappe.query_reports["Location Summary (Quantity)"] = mittal_customization.location_summary.settings(
	{
		report_name: "Location Summary (Quantity)",
		show_value: false,
	}
);
