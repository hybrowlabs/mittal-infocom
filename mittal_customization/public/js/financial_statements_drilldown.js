// Drill-down on Receivable / Payable accounts in the financial statements opens the
// Accounts Receivable Summary and Accounts Payable Summary reports instead of the
// detailed Accounts Receivable / Accounts Payable reports.
//
// Applies wherever erpnext.financial_statements.open_general_ledger is used: the
// Balance Sheet, the Profit and Loss Statement, the Trial Balance and the Tally format
// templates.

frappe.provide("erpnext.financial_statements");
frappe.provide("frappe.query_reports");

(function () {
	const summary_reports = {
		Receivable: "Accounts Receivable Summary",
		Payable: "Accounts Payable Summary",
	};

	const party_account_labels = {
		Receivable: __("Receivable Account"),
		Payable: __("Payable Account"),
	};

	// The summary reports already filter on party_account server side (they share
	// ReceivablePayableReport with the detailed reports) but do not expose the filter,
	// so frappe.route_options would drop the account we drilled down on. Add the field
	// as soon as each report script registers itself.
	Object.keys(summary_reports).forEach((account_type) => {
		const report_name = summary_reports[account_type];
		let settings;

		Object.defineProperty(frappe.query_reports, report_name, {
			configurable: true,
			enumerable: true,
			get() {
				return settings;
			},
			set(value) {
				settings = value;
				add_party_account_filter(value, account_type);
			},
		});
	});

	function add_party_account_filter(settings, account_type) {
		if (!settings || !settings.filters) return;
		if (settings.filters.some((f) => f.fieldname == "party_account")) return;

		const party_index = settings.filters.findIndex((f) => f.fieldname == "party");

		settings.filters.splice(party_index + 1, 0, {
			fieldname: "party_account",
			label: party_account_labels[account_type],
			fieldtype: "Link",
			options: "Account",
			get_query: () => {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
						account_type: account_type,
						is_group: 0,
					},
				};
			},
		});
	}

	// A row carries every account it was built from, one for a ledger and several for a
	// group. Only a single account can be handed to the summary reports, which filter on
	// one party account.
	function single_account(data) {
		const account = data.account || data.accounts;

		if (Array.isArray(account)) {
			return account.length == 1 ? account[0] : null;
		}

		return account || null;
	}

	const open_general_ledger = erpnext.financial_statements.open_general_ledger;

	erpnext.financial_statements.open_general_ledger = function (data) {
		if (!data) return open_general_ledger.apply(this, arguments);
		if (!data.account && !data.accounts) return;

		const account = single_account(data);

		// The Trial Balance does not select account_type, and neither do the rows of a
		// Tally format template, so look it up before deciding which report to open.
		if (data.account_type === undefined && account) {
			frappe.db.get_value("Account", account, "account_type").then((r) => {
				data.account_type = (r.message && r.message.account_type) || "";
				erpnext.financial_statements.open_general_ledger(data);
			});
			return;
		}

		if (!summary_reports[data.account_type] || !account) {
			return open_general_ledger.call(this, data);
		}

		const filters = frappe.query_report.filters;
		const get_value = (fieldname) => {
			const filter = filters.find((f) => f.df.fieldname == fieldname);
			return filter ? filter.get_value() : "";
		};

		frappe.route_options = {
			company: frappe.query_report.get_filter_value("company"),
			party_account: account,
			report_date: data.to_date || data.year_end_date,
			project: get_value("project"),
			cost_center: get_value("cost_center"),
		};

		// carry over the accounting dimensions the statement was filtered on
		filters.forEach((f) => {
			if (f.df.fieldtype != "MultiSelectList") return;
			if (f.df.fieldname in frappe.route_options) return;

			const value = f.get_value();
			if (value && value.length > 0) {
				frappe.route_options[f.df.fieldname] = value;
			}
		});

		frappe.set_route("query-report", summary_reports[data.account_type]);
	};
})();
