// Desk assets for the app.
//
// These are bundled rather than listed one by one in app_include_js so that the built
// file carries a content hash. Assets are served with "cache-control: immutable", so a
// plain path under public/js keeps its name after a deploy and the browser goes on
// running the previous copy.

import "./serial_no_batch_selector.js";
import "./financial_statements_drilldown.js";
import "./tally_statement_print.js";
