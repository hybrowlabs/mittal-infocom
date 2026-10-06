frappe.ui.form.on("Payment Entry", {
	mode_of_payment(frm) {
		if (!frm.doc.mode_of_payment || !frm.doc.company || !frm.fields_dict.branch) {
			return;
		}

		erpnext.accounts.pos.get_payment_mode_account(frm, frm.doc.mode_of_payment, (account) => {
			set_branch_from_payment_account(frm, account);
		});
	},
});

function set_branch_from_payment_account(frm, account) {
	if (!account) {
		return;
	}

	frappe.db.get_value(
		"Mode of Payment Account",
		{
			parenttype: "Mode of Payment",
			parent: frm.doc.mode_of_payment,
			company: frm.doc.company,
			default_account: account,
		},
		"custom_branch",
		(r) => {
			if (!r || !("custom_branch" in r)) {
				return;
			}

			frm.set_value("branch", r.custom_branch || "");
		},
		"Mode of Payment"
	);
}
