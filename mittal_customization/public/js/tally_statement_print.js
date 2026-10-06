// Adds the Tally format print to the financial statements. Frappe v15 cannot attach a
// print format to a report, so the layout is rendered server side and returned as a PDF.

frappe.provide("frappe.query_reports");

(function () {
	const REPORTS = ["Balance Sheet", "Profit and Loss Statement"];

	// each report script registers itself after this file runs, so hook the assignment
	REPORTS.forEach((report_name) => {
		let settings;

		Object.defineProperty(frappe.query_reports, report_name, {
			configurable: true,
			enumerable: true,
			get() {
				return settings;
			},
			set(value) {
				settings = value;
				add_tally_print(value);
			},
		});
	});

	function add_tally_print(settings) {
		if (!settings || settings.tally_print_added) return;
		settings.tally_print_added = true;

		const existing_onload = settings.onload;

		settings.onload = function (report) {
			if (existing_onload) existing_onload.call(this, report);

			report.page.add_inner_button(
				__("Print in Tally Format"),
				() => print_statement(report),
				__("Tally Format")
			);

			report.page.add_inner_button(
				__("Preview in Tally Format"),
				() => preview_statement(report),
				__("Tally Format")
			);
		};
	}

	function get_filters(report) {
		const filters = report.get_filter_values(true);
		if (!filters) return null;

		if (!filters.report_template) {
			frappe.msgprint({
				title: __("Select a Report Template"),
				message: __(
					"Choose a Report Template such as Tally Balance Sheet before printing in the Tally format."
				),
				indicator: "orange",
			});
			return null;
		}

		return filters;
	}

	function print_statement(report) {
		const filters = get_filters(report);
		if (!filters) return;

		open_url_post(
			"/api/method/mittal_customization.tally.print_statement.download_statement_pdf",
			{ filters: JSON.stringify(filters) }
		);
	}

	function preview_statement(report) {
		const filters = get_filters(report);
		if (!filters) return;

		frappe.call({
			method: "mittal_customization.tally.print_statement.preview_statement_html",
			args: { filters: JSON.stringify(filters) },
			freeze: true,
			freeze_message: __("Preparing the statement ..."),
			callback: (r) => {
				if (!r.message) return;

				const preview = window.open("", "_blank");
				preview.document.write(r.message);
				preview.document.close();
			},
		});
	}
})();
