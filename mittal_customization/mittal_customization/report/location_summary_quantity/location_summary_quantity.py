# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""Location Summary without the value columns, for users who may see stock but not
what it is worth.

The figures come from Location Summary itself rather than from a second query, so the
two reports can never disagree on a quantity. Only the presentation differs.
"""

from mittal_customization.mittal_customization.report.location_summary.location_summary import (
	execute as location_summary,
)

VALUE_FIELDS = ("_rate", "_value")


def execute(filters=None):
	columns, data, message = location_summary(filters)

	columns = [d for d in columns if not d["fieldname"].endswith(VALUE_FIELDS)]

	# The values are dropped from the rows too, not just from the columns. A hidden
	# column still travels to the browser, where the reader this report exists for
	# would be able to read it.
	for row in data:
		for fieldname in [d for d in row if d.endswith(VALUE_FIELDS)]:
			del row[fieldname]

	return columns, data, message
