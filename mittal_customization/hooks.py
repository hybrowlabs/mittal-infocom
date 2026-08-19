app_name = "mittal_customization"
app_title = "Mittal Customization"
app_publisher = "SAW India"
app_description = "Serial No and IMEI No 1 Customization"
app_email = "meet@sawindia.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mittal_customization",
# 		"logo": "/assets/mittal_customization/logo.png",
# 		"title": "Mittal Customization",
# 		"route": "/mittal_customization",
# 		"has_permission": "mittal_customization.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mittal_customization/css/mittal_customization.css"
app_include_js = "/assets/mittal_customization/js/serial_no_batch_selector.js"

website_route_rules = [
    {"from_route": "/retailerportal", "to_route": "retailerportal"},
]

# include js, css files in header of web template
# web_include_css = "/assets/mittal_customization/css/mittal_customization.css"
# web_include_js = "/assets/mittal_customization/js/mittal_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mittal_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Journal Entry": "public/js/journal_entry.js",
	"Payment Entry": "public/js/payment_entry.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mittal_customization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mittal_customization.utils.jinja_methods",
# 	"filters": "mittal_customization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mittal_customization.install.before_install"
# after_install = "mittal_customization.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mittal_customization.uninstall.before_uninstall"
# after_uninstall = "mittal_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mittal_customization.utils.before_app_install"
# after_app_install = "mittal_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mittal_customization.utils.before_app_uninstall"
# after_app_uninstall = "mittal_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mittal_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Serial and Batch Bundle": "mittal_customization.overrides.serial_and_batch_bundle.CustomSerialandBatchBundle"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mittal_customization.tasks.all"
# 	],
# 	"daily": [
# 		"mittal_customization.tasks.daily"
# 	],
# 	"hourly": [
# 		"mittal_customization.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mittal_customization.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mittal_customization.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mittal_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.is_serial_batch_no_exists": "mittal_customization.overrides.serial_and_batch_bundle.is_serial_batch_no_exists",
	"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_serial_batch_ledgers": "mittal_customization.overrides.serial_and_batch_bundle.get_serial_batch_ledgers",
	"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.add_serial_batch_ledgers": "mittal_customization.overrides.serial_and_batch_bundle.add_serial_batch_ledgers",
	"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.upload_csv_file": "mittal_customization.overrides.serial_and_batch_bundle.upload_csv_file",
	"erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.get_auto_data": "mittal_customization.overrides.serial_and_batch_bundle.get_auto_data",
	"mittal_customization.customer_portal_api.get_ledger": "mittal_customization.customer_portal_api.get_ledger",
	"mittal_customization.customer_portal_api.get_outstanding": "mittal_customization.customer_portal_api.get_outstanding",
	"mittal_customization.customer_portal_api.get_payments": "mittal_customization.customer_portal_api.get_payments",
	"mittal_customization.customer_portal_api.get_invoice_pdf": "mittal_customization.customer_portal_api.get_invoice_pdf",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mittal_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mittal_customization.utils.before_request"]
# after_request = ["mittal_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["mittal_customization.utils.before_job"]
# after_job = ["mittal_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mittal_customization.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
