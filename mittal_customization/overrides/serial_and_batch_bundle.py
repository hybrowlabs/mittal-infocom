import csv
import re

import frappe
from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import (
	SerialandBatchBundle,
	get_auto_batch_nos,
	get_batch,
	get_non_expired_batches,
	get_reference_serial_and_batch_bundle,
	get_reserved_serial_nos,
	get_serial_nos_based_on_posting_date,
	get_type_of_transaction,
	make_batch_no,
	make_batch_nos,
	parse_csv_file_to_get_serial_batch,
)
from frappe import _, bold
from frappe.utils import cint, flt, now, nowtime, parse_json


class CustomSerialandBatchBundle(SerialandBatchBundle):
	def throw_error_message(self, message, exception=frappe.ValidationError):
		"""
		Customization Code Showcase Scan Value

		Core builds its messages with the Serial No name, which here is a random
		10 char hash. Mittal users only ever see the scanned IMEI / Serial No ID,
		so swap the serial names for their scan value before throwing. Only the
		values labelled as a serial no are touched, so warehouse names and other
		bolded text in the message are left alone. The validation logic itself
		stays in erpnext and keeps receiving upstream fixes.
		"""
		def to_scan_values(match):
			scan_values = []
			for serial_no in match.group(2).split(", "):
				scan_value = frappe.db.get_value(
					"Serial No", serial_no, ["custom_imei_no_1", "custom_serial_no_id"], as_dict=True
				)
				scan_values.append(
					(scan_value and (scan_value.custom_imei_no_1 or scan_value.custom_serial_no_id))
					or serial_no
				)

			return match.group(1) + bold(", ".join(scan_values))

		message = re.sub(r"(Serial Nos? )<strong>(.*?)</strong>", to_scan_values, message)

		super().throw_error_message(message, exception)

	def on_submit(self):
		super().on_submit()

		for entry in self.entries:
			if not frappe.db.get_value("Serial No", entry.serial_no, "custom_imei_no_1"):
				frappe.db.set_value("Serial No", entry.serial_no, "custom_imei_no_1", entry.custom_imei_no_1)

			if not frappe.db.get_value("Serial No", entry.serial_no, "custom_serial_no_id"):
				frappe.db.set_value(
					"Serial No", entry.serial_no, "custom_serial_no_id", entry.custom_serial_no_id
				)


@frappe.whitelist()
def get_auto_data(**kwargs):
	kwargs = frappe._dict(kwargs)
	if cint(kwargs.has_serial_no):
		return get_available_serial_nos(kwargs)

	elif cint(kwargs.has_batch_no):
		return get_auto_batch_nos(kwargs)


def get_available_serial_nos(kwargs):
	"""
	Customization Code Showcase Serial No ID, IMEI No 1, IMEI No 2
	"""
	fields = ["name as serial_no", "warehouse", "custom_serial_no_id", "custom_imei_no_1", "custom_imei_no_2"]
	if kwargs.has_batch_no:
		fields.append("batch_no")

	order_by = "creation"
	if kwargs.based_on == "LIFO":
		order_by = "creation desc"
	elif kwargs.based_on == "Expiry":
		order_by = "amc_expiry_date asc"

	filters = {"item_code": kwargs.item_code}

	# ignore_warehouse is used for backdated stock transactions
	# There might be chances that the serial no not exists in the warehouse during backdated stock transactions
	if not kwargs.get("ignore_warehouse"):
		filters["warehouse"] = ("is", "set")
		if kwargs.warehouse:
			filters["warehouse"] = kwargs.warehouse

	# Since SLEs are not present against Reserved Stock [POS invoices, SRE], need to ignore reserved serial nos.
	ignore_serial_nos = get_reserved_serial_nos(kwargs)

	# To ignore serial nos in the same record for the draft state
	if kwargs.get("ignore_serial_nos"):
		ignore_serial_nos.extend(kwargs.get("ignore_serial_nos"))

	if kwargs.get("posting_date"):
		if kwargs.get("posting_time") is None:
			kwargs.posting_time = nowtime()

		time_based_serial_nos = get_serial_nos_based_on_posting_date(kwargs, ignore_serial_nos)

		if not time_based_serial_nos:
			return []

		filters["name"] = ("in", time_based_serial_nos)
	elif ignore_serial_nos:
		filters["name"] = ("not in", ignore_serial_nos)

	if kwargs.get("batches"):
		batches = get_non_expired_batches(kwargs.get("batches"))
		if not batches:
			return []

		filters["batch_no"] = ("in", batches)

	return frappe.get_all(
		"Serial No",
		fields=fields,
		filters=filters,
		limit=cint(kwargs.qty) or 10000000,
		order_by=order_by,
	)


@frappe.whitelist()
def upload_csv_file(item_code, file_path):
	serial_nos, batch_nos = [], []
	serial_nos, batch_nos = get_serial_batch_from_csv(item_code, file_path)

	return {
		"serial_nos": serial_nos,
		"batch_nos": batch_nos,
	}


def get_serial_batch_from_csv(item_code, file_path):
	if "private" in file_path:
		file_path = frappe.get_site_path() + file_path
	else:
		file_path = frappe.get_site_path() + "/public" + file_path

	serial_nos = []
	batch_nos = []

	with open(file_path) as f:
		reader = csv.reader(f)
		serial_nos, batch_nos = parse_csv_file_to_get_serial_batch(reader)

	if serial_nos:
		"""
			Customization Code Function Override
		"""
		make_serial_nos(item_code, serial_nos)

	if batch_nos:
		make_batch_nos(item_code, batch_nos)

	for serial_no in serial_nos:
		details = get_serial_no_from_imei_no(serial_no.get("serial_no", ""))
		serial_no["serial_no"] = details.get("serial_no")
		serial_no["custom_serial_no_id"] = details.get("custom_serial_no_id")
		serial_no["custom_imei_no_1"] = details.get("custom_imei_no_1")

	return serial_nos, batch_nos


def make_serial_nos(item_code, serial_nos):
	"""
	Customization Code Function Code for Serial No ID and IMEI No
	"""
	item = frappe.get_cached_value(
		"Item", item_code, ["description", "item_code", "item_name", "warranty_period"], as_dict=1
	)

	# serial_nos = [d.get("serial_no").strip() for d in serial_nos if d.get("serial_no")]
	# existing_serial_nos = frappe.get_all("Serial No", filters={"name": ("in", serial_nos)})

	# existing_serial_nos = [d.get("name") for d in existing_serial_nos if d.get("name")]
	# serial_nos = list(set(serial_nos) - set(existing_serial_nos))

	filtered_serial_nos = []
	existing_serial_nos = []

	for d in serial_nos:
		serial_no = d.get("serial_no", "").strip()
		if not serial_no:
			continue

		filters = (
			{"custom_imei_no_1": serial_no}
			if serial_no.isdigit() and len(serial_no) == 15
			else {"custom_serial_no_id": serial_no}
		)

		existing = frappe.db.get_value("Serial No", filters, "name")
		if existing:
			existing_serial_nos.append(existing)
		else:
			filtered_serial_nos.append(serial_no)

	serial_nos = list(set(filtered_serial_nos))

	if not serial_nos:
		return

	serial_nos_details = []
	user = frappe.session.user
	for serial_no in serial_nos:
		unique_id = generate_unique_serial_no()
		serial_nos_details.append(
			(
				unique_id,
				unique_id,
				now(),
				now(),
				user,
				user,
				item.item_code,
				item.item_name,
				item.description,
				item.warranty_period or 0,
				"Inactive",
				serial_no if serial_no.isdigit() and len(serial_no) == 15 else "",
				"" if serial_no.isdigit() and len(serial_no) == 15 else serial_no,
			)
		)

	fields = [
		"name",
		"serial_no",
		"creation",
		"modified",
		"owner",
		"modified_by",
		"item_code",
		"item_name",
		"description",
		"warranty_period",
		"status",
		"custom_imei_no_1",
		"custom_serial_no_id",
	]

	frappe.db.bulk_insert("Serial No", fields=fields, values=set(serial_nos_details))

	frappe.msgprint(_("Serial Nos are created successfully"), alert=True)


@frappe.whitelist()
def is_serial_batch_no_exists(
	item_code,
	type_of_transaction,
	warehouse,
	serial_no=None,
	batch_no=None,
	doctype=None,
	fieldname=None,
	party_name=None,
):
	if serial_no.isdigit() and len(serial_no) == 15:
		filters = {"custom_imei_no_1": serial_no}
	else:
		filters = {"custom_serial_no_id": serial_no}

	serial_no_value = frappe.db.get_value("Serial No", filters, "name")

	if serial_no_value and party_name and doctype in ["Delivery Note", "Sales Invoice"]:
		if frappe.db.get_value("Serial No", serial_no_value, "status") != "Delivered":
			frappe.throw(_("Serial No <b>{0}</b> is not delivered so you can't return it").format(serial_no))
		query = f"""
			SELECT
				sbb.voucher_type,
				sbb.voucher_no
			FROM
				`tabSerial and Batch Entry` as sbe
			LEFT JOIN
				`tabSerial and Batch Bundle` as sbb on sbb.name = sbe.parent
			WHERE
				sbe.serial_no = '{serial_no_value}'
				AND sbb.docstatus = 1
				AND sbb.type_of_transaction = 'Outward'
				AND sbb.voucher_type in ('Sales Invoice', 'Delivery Note')
			ORDER BY
				sbe.creation DESC
			LIMIT 1
		"""
		result = frappe.db.sql(query, as_dict=1)
		if result:
			customer = frappe.db.get_value(
				result[0].get("voucher_type"), result[0].get("voucher_no"), "customer"
			)
			if party_name != customer:
				frappe.throw(
					_(
						"Serial No <b>{0}</b> is already sell to other customer <b>{1}</b> in the voucher <b>{2}</b>"
					).format(serial_no, customer, result[0].get("voucher_no"))
				)
		else:
			frappe.throw(_("Serial No <b>{0}</b> is not sell in the system").format(serial_no))

	elif serial_no_value and party_name and doctype in ["Purchase Invoice", "Purchase Receipt"]:
		if frappe.db.get_value("Serial No", serial_no_value, "status") != "Active":
			frappe.throw(_("Serial No <b>{0}</b> is not active in the system").format(serial_no))
		query = f"""
			SELECT
				sbb.voucher_type,
				sbb.voucher_no
			FROM
				`tabSerial and Batch Entry` as sbe
			LEFT JOIN
				`tabSerial and Batch Bundle` as sbb on sbb.name = sbe.parent
			WHERE
				sbe.serial_no = '{serial_no_value}'
				AND sbb.docstatus = 1
				AND sbb.type_of_transaction = 'Inward'
				AND sbb.voucher_type in ('Purchase Invoice', 'Purchase Receipt')
			ORDER BY
				sbe.creation DESC
			LIMIT 1
		"""
		result = frappe.db.sql(query, as_dict=1)
		if result:
			supplier = frappe.db.get_value(
				result[0].get("voucher_type"), result[0].get("voucher_no"), "supplier"
			)
			if party_name != supplier:
				frappe.throw(
					_(
						"Serial No <b>{0}</b> is already buy from other supplier <b>{1}</b> in the voucher <b>{2}</b>"
					).format(serial_no, supplier, result[0].get("voucher_no"))
				)
		else:
			frappe.throw(_("Serial No <b>{0}</b> is not buy in the system").format(serial_no))

	if serial_no and not serial_no_value and not frappe.db.exists("Serial No", serial_no_value):
		if type_of_transaction != "Inward":
			frappe.throw(_("Serial No {0} does not exists").format(serial_no))

		make_serial_no(serial_no, item_code)

	if (
		serial_no
		and not frappe.db.exists("Serial No", {"warehouse": warehouse, "name": serial_no_value})
		and type_of_transaction != "Inward"
	):
		if doctype != "Stock Entry":
			frappe.throw(
				_("Serial No <b>{0}</b> does not exists in the warehouse <b>{1}</b>").format(
					serial_no, warehouse
				)
			)

	print(warehouse, "----------------")
	if (
		serial_no
		and not frappe.db.exists(
			"Serial No", {"warehouse": warehouse, "name": serial_no_value, "status": ["!=", "Delivered"]}
		)
		and type_of_transaction != "Inward"
		and doctype == "Stock Entry"
	):
		frappe.throw(
			_("Serial No <b>{0}</b> does not exists in the warehouse <b>{1}</b>").format(serial_no, warehouse)
		)

	if batch_no and not frappe.db.exists("Batch", batch_no):
		if type_of_transaction != "Inward":
			frappe.throw(_("Batch No {0} does not exists").format(batch_no))

		make_batch_no(batch_no, item_code)


def generate_unique_serial_no():
	while True:
		new_serial = frappe.generate_hash(length=10)
		if not frappe.db.exists("Serial No", {"serial_no": new_serial}):
			return new_serial


def make_serial_no(serial_no, item_code):
	serial_no_doc = frappe.new_doc("Serial No")
	serial_no_doc.serial_no = generate_unique_serial_no()
	serial_no_doc.item_code = item_code

	if serial_no.isdigit() and len(serial_no) == 15:
		serial_no_doc.custom_imei_no_1 = serial_no
	else:
		serial_no_doc.custom_serial_no_id = serial_no

	serial_no_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_serial_batch_ledgers(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = get_filters_for_bundle(
		item_code=item_code, docstatus=docstatus, voucher_no=voucher_no, name=name, child_row=child_row
	)

	if not filters:
		return

	fields = [
		"`tabSerial and Batch Bundle`.`item_code`",
		"`tabSerial and Batch Entry`.`qty`",
		"`tabSerial and Batch Entry`.`warehouse`",
		"`tabSerial and Batch Entry`.`batch_no`",
		"`tabSerial and Batch Entry`.`serial_no`",
		"`tabSerial and Batch Entry`.`name` as `child_row`",
		"`tabSerial and Batch Entry`.`custom_serial_no_id`",
		"`tabSerial and Batch Entry`.`custom_imei_no_1`",
		"`tabSerial and Batch Entry`.`custom_imei_no_2`",
	]

	if not child_row:
		fields.append("`tabSerial and Batch Bundle`.`name`")

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=fields,
		filters=filters,
		order_by="`tabSerial and Batch Entry`.`idx`",
	)


def get_filters_for_bundle(item_code=None, docstatus=None, voucher_no=None, name=None, child_row=None):
	filters = [
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	if child_row and isinstance(child_row, str):
		child_row = parse_json(child_row)

	if not name and child_row:
		bundle = get_reference_serial_and_batch_bundle(child_row)
		if bundle:
			voucher_no = None
			filters.append(["Serial and Batch Bundle", "name", "=", bundle])
		else:
			return

	if item_code:
		filters.append(["Serial and Batch Bundle", "item_code", "=", item_code])

	if not docstatus:
		docstatus = [0, 1]

	if isinstance(docstatus, list):
		filters.append(["Serial and Batch Bundle", "docstatus", "in", docstatus])
	else:
		filters.append(["Serial and Batch Bundle", "docstatus", "=", docstatus])

	if voucher_no:
		filters.append(["Serial and Batch Bundle", "voucher_no", "=", voucher_no])

	if name:
		if isinstance(name, list):
			filters.append(["Serial and Batch Entry", "parent", "in", name])
		else:
			filters.append(["Serial and Batch Entry", "parent", "=", name])

	return filters


@frappe.whitelist()
def add_serial_batch_ledgers(entries, child_row, doc, warehouse, do_not_save=False) -> object:
	if isinstance(child_row, str):
		child_row = frappe._dict(parse_json(child_row))

	if isinstance(entries, str):
		entries = parse_json(entries)

	parent_doc = doc
	if parent_doc and isinstance(parent_doc, str):
		parent_doc = parse_json(parent_doc)

	bundle = child_row.serial_and_batch_bundle
	if child_row.get("is_rejected"):
		bundle = child_row.rejected_serial_and_batch_bundle

	if frappe.db.exists("Serial and Batch Bundle", bundle):
		sb_doc = update_serial_batch_no_ledgers(bundle, entries, child_row, parent_doc, warehouse)
	else:
		sb_doc = create_serial_batch_no_ledgers(
			entries, child_row, parent_doc, warehouse, do_not_save=do_not_save
		)

	return sb_doc


def create_serial_batch_no_ledgers(
	entries, child_row, parent_doc, warehouse=None, do_not_save=False
) -> object:
	warehouse = warehouse or (child_row.rejected_warehouse if child_row.is_rejected else child_row.warehouse)

	type_of_transaction = get_type_of_transaction(parent_doc, child_row)
	if parent_doc.get("doctype") == "Stock Entry":
		warehouse = warehouse or child_row.s_warehouse or child_row.t_warehouse

	doc = frappe.get_doc(
		{
			"doctype": "Serial and Batch Bundle",
			"voucher_type": child_row.parenttype,
			"item_code": child_row.item_code,
			"warehouse": warehouse,
			"is_rejected": child_row.is_rejected,
			"type_of_transaction": type_of_transaction,
			"posting_date": parent_doc.get("posting_date"),
			"posting_time": parent_doc.get("posting_time"),
			"company": parent_doc.get("company"),
		}
	)

	batch_no = None

	if (
		not entries[0].get("batch_no")
		and entries[0].get("serial_no")
		and frappe.get_cached_value("Item", child_row.item_code, "has_batch_no")
	):
		batch_no = get_batch(child_row.item_code)

	for row in entries:
		row = frappe._dict(row)
		doc.append(
			"entries",
			{
				"qty": (flt(row.qty) or 1.0) * (1 if type_of_transaction == "Inward" else -1),
				"warehouse": warehouse,
				"batch_no": row.batch_no or batch_no,
				"serial_no": row.serial_no,
				"custom_serial_no_id": row.custom_serial_no_id,
				"custom_imei_no_1": row.custom_imei_no_1,
				"custom_imei_no_2": row.custom_imei_no_2,
			},
		)

	doc.save()

	if do_not_save:
		frappe.db.set_value(child_row.doctype, child_row.name, "serial_and_batch_bundle", doc.name)

	frappe.msgprint(_("Serial and Batch Bundle created"), alert=True)

	return doc


def update_serial_batch_no_ledgers(bundle, entries, child_row, parent_doc, warehouse=None) -> object:
	doc = frappe.get_doc("Serial and Batch Bundle", bundle)
	doc.voucher_detail_no = child_row.name
	doc.posting_date = parent_doc.posting_date
	doc.posting_time = parent_doc.posting_time
	doc.warehouse = warehouse or doc.warehouse
	doc.set("entries", [])

	for d in entries:
		doc.append(
			"entries",
			{
				"qty": (flt(d.get("qty")) or 1.0) * (1 if doc.type_of_transaction == "Inward" else -1),
				"warehouse": warehouse or d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
				"custom_serial_no_id": d.get("custom_serial_no_id"),
				"custom_imei_no_1": d.get("custom_imei_no_1"),
				"custom_imei_no_2": d.get("custom_imei_no_2"),
			},
		)

	doc.save(ignore_permissions=True)

	frappe.msgprint(_("Serial and Batch Bundle updated"), alert=True)

	return doc


"""
	Custom Whitelist Function
"""


@frappe.whitelist()
def get_serial_no_from_imei_no(imei_no):
	if imei_no.isdigit() and len(imei_no) == 15:
		return {
			"serial_no": frappe.db.get_value("Serial No", {"custom_imei_no_1": imei_no}, "serial_no"),
			"custom_serial_no_id": frappe.db.get_value(
				"Serial No", {"custom_imei_no_1": imei_no}, "custom_serial_no_id"
			),
			"custom_imei_no_1": imei_no,
		}
	else:
		return {
			"serial_no": frappe.db.get_value("Serial No", {"custom_serial_no_id": imei_no}, "serial_no"),
			"custom_serial_no_id": imei_no,
			"custom_imei_no_1": frappe.db.get_value(
				"Serial No", {"custom_serial_no_id": imei_no}, "custom_imei_no_1"
			),
		}
