// Shared settings for the two Location Summary reports.
//
// "Location Summary" carries Rate and Value, "Location Summary (Quantity)" does not.
// Everything else about them -- filters, the tree layout, the Tally format export and
// the help -- is the same, so it is defined once here and both report scripts ask for
// it. Keeping one definition is what stops the two reports drifting apart.

frappe.provide("mittal_customization.location_summary");

mittal_customization.location_summary.settings = function (options) {
	const report_name = options.report_name;
	const show_value = options.show_value !== false;

	return {
		filters: [
			{
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				reqd: 1,
			},
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				default:
					frappe.defaults.get_user_default("year_start_date") ||
					frappe.datetime.year_start(),
				reqd: 1,
			},
			{
				fieldname: "to_date",
				label: __("As On Date"),
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "warehouse",
				label: __("Warehouse"),
				fieldtype: "MultiSelectList",
				get_data: function (txt) {
					return frappe.db.get_link_options("Warehouse", txt, {
						company: frappe.query_report.get_filter_value("company"),
						is_group: 0,
						disabled: 0,
					});
				},
			},
			{
				fieldname: "item_group",
				label: __("Item Group"),
				fieldtype: "Link",
				options: "Item Group",
			},
			{
				fieldname: "show_total_column",
				label: __("Show Total Column"),
				fieldtype: "Check",
				default: 1,
			},
			{
				fieldname: "show_zero_stock",
				label: __("Show Items with Zero Stock"),
				fieldtype: "Check",
				default: 0,
			},
		],

		tree: true,
		name_field: "particulars",
		parent_field: "parent_particulars",
		initial_depth: 2,

		onload: function (report) {
			report.page.add_inner_button(
				__("Download in Tally Format"),
				() => download_tally_format(report, report_name),
				__("Export")
			);

			report.page.add_inner_button(
				__("How to Read This Report"),
				() => show_help_dialog(show_value),
				__("Help")
			);
		},

		formatter: function (value, row, column, data, default_formatter) {
			value = default_formatter(value, row, column, data);

			if (data && data.is_group_row) {
				value = `<span style="font-weight: 600">${value}</span>`;
			}

			return value;
		},
	};
};

function download_tally_format(report, report_name) {
	const filters = report.get_filter_values(true);
	if (!filters) {
		return;
	}

	open_url_post(
		"/api/method/mittal_customization.mittal_customization.report.location_summary.tally_export.download_tally_format",
		{ filters: JSON.stringify(filters), report_name: report_name }
	);
}

function show_help_dialog(show_value) {
	const dialog = new frappe.ui.Dialog({
		title: __("How to Read This Report"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "help" }],
		primary_action_label: __("Close"),
		primary_action: () => dialog.hide(),
	});

	dialog.fields_dict.help.$wrapper.html(help_html(show_value));
	dialog.show();
}

function column_help(show_value) {
	if (!show_value) {
		return `
	<div>${__("Each location has one column:")}</div>
	<table>
		<tr><th>${__("Quantity")}</th><td>${__(
			"Units lying in that location on the As On Date."
		)}</td></tr>
	</table>
	<ul style="margin-top: 8px">
		<li>${__("A blank cell means there is no stock of that item in that location.")}</li>
	</ul>
	<div class="note">${__(
		"This report shows quantities only. The value of the stock is reported separately in <b>Location Summary</b>."
	)}</div>`;
	}

	return `
	<div>${__("Each location has three columns:")}</div>
	<table>
		<tr><th>${__("Quantity")}</th><td>${__(
			"Units lying in that location on the As On Date."
		)}</td></tr>
		<tr><th>${__("Rate")}</th><td>${__(
			"Average value per unit, calculated as Value divided by Quantity."
		)}</td></tr>
		<tr><th>${__("Value")}</th><td>${__("Total stock value in that location.")}</td></tr>
	</table>
	<ul style="margin-top: 8px">
		<li>${__("A blank cell means there is no stock of that item in that location.")}</li>
		<li>${__(
			"Rate is left blank on the Grand Total row, because an average rate across different products has no meaning."
		)}</li>
	</ul>
	<div class="note">${__(
		"<b>Rate is not a selling price or a purchase price.</b> It is the average value at which the stock is currently carried in the books, so it changes as stock is bought at different costs."
	)}</div>`;
}

function help_html(show_value) {
	return `
<div class="ls-help" style="font-size: var(--text-md); line-height: 1.6; color: var(--text-color)">
	<style>
		.ls-help h5 { margin: 18px 0 6px; font-weight: 600; }
		.ls-help h5:first-child { margin-top: 0; }
		.ls-help ul { padding-left: 20px; margin-bottom: 0; }
		.ls-help li { margin-bottom: 4px; }
		.ls-help table { width: 100%; margin-top: 6px; }
		.ls-help th, .ls-help td {
			padding: 6px 8px; border-bottom: 1px solid var(--border-color); text-align: left;
			vertical-align: top;
		}
		.ls-help th { font-weight: 600; white-space: nowrap; }
		.ls-help .note {
			background: var(--bg-light-gray); border-left: 3px solid var(--border-color);
			padding: 8px 12px; margin-top: 8px; border-radius: var(--border-radius);
		}
	</style>

	<h5>${__("What this report shows")}</h5>
	<div>${__(
		"The closing stock as on the <b>As On Date</b>, for every location, arranged by item group. It is the position at the end of that date, not the movement during a period."
	)}</div>

	<h5>${__("Reading the rows")}</h5>
	<ul>
		<li>${__("Rows follow the Item Group tree. Bold rows are groups; click the arrow to expand.")}</li>
		<li>${__("A group row is the total of everything below it, including sub-groups.")}</li>
		<li>${__("The last row is the Grand Total for all groups shown.")}</li>
	</ul>

	<h5>${__("Reading the columns")}</h5>
	${column_help(show_value)}

	<h5>${__("Filters")}</h5>
	<table>
		<tr><th>${__("From Date")}</th><td>${__(
			"Sets the period the statement is presented for, shown above the report and in the Tally format export. The figures are a closing balance, so they depend only on the As On Date."
		)}</td></tr>
		<tr><th>${__("As On Date")}</th><td>${__(
			"Any past date can be used, for example a year end, to see the position on that date."
		)}</td></tr>
		<tr><th>${__("Warehouse")}</th><td>${__(
			"Leave blank for all locations, or pick a few to compare them side by side."
		)}</td></tr>
		<tr><th>${__("Item Group")}</th><td>${__(
			"Restricts the report to one branch of the item group tree."
		)}</td></tr>
		<tr><th>${__("Show Total Column")}</th><td>${__(
			"Adds a combined total across the locations shown."
		)}</td></tr>
		<tr><th>${__("Show Items with Zero Stock")}</th><td>${__(
			"Also lists items that moved during the period but ended at zero."
		)}</td></tr>
	</table>

	<h5>${__("Excel in Tally format")}</h5>
	<div>${__(
		"<b>Export &gt; Download in Tally Format</b> produces an Excel file laid out the way Tally prints this statement, with the letterhead, the period, and the columns grouped under each location. The figures are exactly those on screen."
	)}</div>

	<h5>${__("How to check the figures")}</h5>
	<ul>
		<li>${__(
			"Open the standard <b>Stock Balance</b> report for the same date and location. Balance Qty will match this report exactly, as both are built on the same stock ledger."
		)}</li>
		<li>${__(
			"Click the Item Code on any row to open the item, or use the <b>Stock Ledger</b> report to see every movement behind a figure."
		)}</li>
		<li>${__(
			"For serialised items, the serial numbers held in a location are the physical check on the quantity."
		)}</li>
	</ul>
	<div class="note">${__(
		"If this report disagrees with the quantity shown on the item dashboard, the difference is in the underlying stock data, not in the report. Please report it rather than adjusting stock to match."
	)}</div>
</div>`;
}
