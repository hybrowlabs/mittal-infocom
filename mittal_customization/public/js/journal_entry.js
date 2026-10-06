frappe.ui.form.on("Journal Entry", {
	from_template: function (frm) {
		if (frm.doc.from_template) {
			setTimeout(() => {
				frappe.db.get_doc("Journal Entry Template", frm.doc.from_template).then((doc) => {
					frappe.model.clear_table(frm.doc, "accounts");
					frm.set_value({
						company: doc.company,
						voucher_type: doc.voucher_type,
						naming_series: doc.naming_series,
						is_opening: doc.is_opening,
						multi_currency: doc.multi_currency,
					});
					update_jv_details(frm.doc, doc.accounts);
				});
			}, 300);
		}
	},
});

var update_jv_details = function (doc, r) {
	$.each(r, function (i, d) {
		var row = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
		frappe.model.set_value(row.doctype, row.name, "account", d.account);
        frappe.model.set_value(row.doctype, row.name, "branch", d.custom_branch);
	});
	refresh_field("accounts");
};

