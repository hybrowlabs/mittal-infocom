# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class TallyAccountGroup(Document):
	@property
	def label(self):
		return self.display_label or self.tally_group_name
