# Copyright (c) 2025, Rishabh Pandram and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import datetime
from frappe.model.document import Document

@frappe.whitelist()
def create_log(lead, geolocation):
	city = geolocation.get("city", {}).get("name", "N/A")
	country = geolocation.get("country", {}).get("name", "N/A")
	current_time = datetime.datetime.now()
	log = frappe.get_doc({
		'doctype': 'Website Visitors Log',
		'email_id': lead.email_id,
		'lead': lead,
		'city': city,
		'country': country,
		'visited_at': current_time
	})
	log.insert(ignore_permissions=True)
	frappe.db.commit()

class WebsiteVisitorsLog(Document):
	@staticmethod
	def clear_old_logs(days=180):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Website Visitors Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

