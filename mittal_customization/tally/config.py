# Copyright (c) 2026, SAW India and contributors
# For license information, please see license.txt

"""How the chart of accounts is presented on the Tally format statements.

The chart of accounts was migrated from Tally, so its own group structure already
matches the Tally statement. A line on the statement is therefore derived from the
tree: the block is the group directly below the root, and the line is the next group
below the block -- or the ledger itself when it sits directly under the block. That
rule reproduces the Tally print exactly, so only the handful of differences below
need to be stated.
"""

# Tally prints these groups under a different heading than the chart of accounts uses.
DISPLAY_LABELS = {
	"Accounts Receivable": "Sundry Debtors",
	"Cash In Hand": "Cash-in-hand",
	"GST Receivable/Payable": "Gst Receivable / Payable",
	"Reserve and surplus": "Reserves & Surplus",
	"Stock In Hand": "Closing Stock",
}

# Tally prints these as a block of their own instead of nesting them where the chart
# of accounts puts them.
BLOCK_OVERRIDES = {
	"Loans (Liabilities)": "Loans (Liability)",
	"Branch/Divisions": "Branch / Divisions",
	"Branch/Divisions Goa": "Branch / Divisions",
}

# Order the blocks are printed in, per side. Blocks not listed follow, alphabetically.
BLOCK_ORDER = {
	"Liabilities": [
		"Capital Account",
		"Loans (Liability)",
		"Current Liabilities",
		"Branch / Divisions",
		"Profit & Loss A/c",
	],
	"Assets": [
		"Fixed Assets",
		"Investments",
		"Current Assets",
		"Branch / Divisions",
		"Temporary Accounts",
	],
	"Expenses": [
		"Direct Expenses",
		"Branch Purchase",
		"Indirect Expenses",
		"Other Expenses",
	],
	"Income": [
		"Sales Accounts",
		"Direct Income",
		"Indirect Income",
		"Other Income",
	],
}

# The profit and loss statement is printed in two halves. These blocks make up the
# trading account, which closes at Gross Profit; everything else falls below it and
# closes at Nett Profit.
TRADING_BLOCKS = {
	"Expenses": ("Direct Expenses", "Branch Purchase"),
	"Income": ("Sales Accounts", "Direct Income"),
}

# Where a ledger posted directly against the root group is printed, so that nothing is
# left off the statement.
OTHER_BLOCK = {
	"Liabilities": "Other Liabilities",
	"Assets": "Other Assets",
	"Income": "Other Income",
	"Expenses": "Other Expenses",
}

# The block a ledger falls into when it sits directly under the root group.
ROOT_LEVEL_BLOCK = {
	"Profit and Loss Account": "Profit & Loss A/c",
}

SIDE_BY_ROOT_TYPE = {
	"Asset": "Assets",
	"Liability": "Liabilities",
	"Income": "Income",
	"Expense": "Expenses",
}
