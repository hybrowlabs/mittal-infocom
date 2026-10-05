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

	// A row carries every account it was built from: one account for a ledger line,
	// several for a group line such as "Sundry Debtors" or "Sundry Creditors".
	function account_list(data) {
		const account = data.account || data.accounts;

		if (Array.isArray(account)) return account.filter(Boolean);

		return account ? [account] : [];
	}

	// The party type a row drills down to, or "" for the general ledger.
	//
	// A single ledger is decided by its own account_type. A group line is only a party
	// group when every one of its ledgers is the same party type, or when the group
	// account they hang off is itself typed -- "Sundry Creditors - MIPL" is a Payable
	// group whose ledgers are mostly untyped. Ignoring untyped ledgers instead would
	// misread a mixed group: "Loans & Advances (Asset)" holds one receivable among six
	// plain ledgers, and belongs in the general ledger.
	//
	// Sent as a POST: a group can hold a couple of hundred accounts, which is past what
	// a query string takes.
	function party_type_of(accounts) {
		return frappe
			.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Account",
					filters: { name: ["in", accounts] },
					fields: ["account_type", "parent_account"],
					limit_page_length: 0,
				},
			})
			.then((r) => {
				const rows = r.message || [];
				if (!rows.length) return "";

				const types = new Set(rows.map((row) => row.account_type || ""));
				if (types.size == 1) {
					const [type] = Array.from(types);
					if (summary_reports[type]) return type;
				}

				// Fall back to the group the ledgers hang off, but only for a group
				// line. A single untyped ledger keeps going to the general ledger: its
				// parent being a party group says nothing about the ledger itself, and
				// the summary filtered on it would come back empty.
				if (rows.length < 2) return "";

				// Only when they share one group, so a row spanning several is not
				// mistyped.
				const parents = new Set(rows.map((row) => row.parent_account || ""));
				if (parents.size != 1) return "";

				const [parent] = Array.from(parents);
				if (!parent) return "";

				return frappe.db.get_value("Account", parent, "account_type").then((p) => {
					const type = (p.message && p.message.account_type) || "";
					return summary_reports[type] ? type : "";
				});
			});
	}

	const open_general_ledger = erpnext.financial_statements.open_general_ledger;

	erpnext.financial_statements.open_general_ledger = function (data) {
		if (!data) return open_general_ledger.apply(this, arguments);
		if (!data.account && !data.accounts) return;

		const accounts = account_list(data);

		// Neither the Trial Balance nor a row of a Tally format template selects
		// account_type, so resolve it from the accounts before choosing the report.
		// Assigning "" rather than leaving it undefined terminates the recursion.
		if (data.account_type === undefined && accounts.length) {
			party_type_of(accounts).then((account_type) => {
				data.account_type = account_type;
				erpnext.financial_statements.open_general_ledger(data);
			});
			return;
		}

		if (!summary_reports[data.account_type] || !accounts.length) {
			return open_general_ledger.call(this, data);
		}

		const filters = frappe.query_report.filters;
		const get_value = (fieldname) => {
			const filter = filters.find((f) => f.df.fieldname == fieldname);
			return filter ? filter.get_value() : "";
		};

		frappe.route_options = {
			company: frappe.query_report.get_filter_value("company"),
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

		// The summary reports filter on a single party ledger. A group line covers
		// several of them, and a statement row for a group account hands over the group
		// itself, which carries no postings. Leave the filter unset in both cases, so
		// the report falls back to every account of this type in the company. The
		// Balance Sheet calls the flag is_group, the Trial Balance is_group_account.
		const is_group = data.is_group || data.is_group_account;

		if (accounts.length == 1 && !is_group) {
			frappe.route_options.party_account = accounts[0];
		}

		frappe.set_route("query-report", summary_reports[data.account_type]);
	};
})();
