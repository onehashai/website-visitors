# Copyright (c) 2025, Rishabh Pandram and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document
	
def update_visitor_details(lead, fingerprint):
	visitor_details_json = json.dumps(fingerprint)

	frappe.db.set_value("Lead", lead.name, {
        "visit_count": lead.visit_count + 1,
        "visitor_details": visitor_details_json
    }, update_modified=False)
	frappe.db.commit()
	
def create_new_entry_in_child_table(log, page_info):
	from datetime import datetime

	page_open_time_dt = datetime.strptime(page_info["page_open_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
	page_close_time_dt = datetime.strptime(page_info["page_close_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
	time_spent = (page_close_time_dt - page_open_time_dt).total_seconds()
	log.append("session_duration",{
		"page": page_info["page_url"],
		"time_spent": time_spent
    })
	log.save(ignore_permissions=True, ignore_version=True)

def update_on_website(lead):
	lead = frappe.get_doc("Lead", lead.name, ignore_permissions=True)
	lead.on_website = 1
	lead.save(ignore_permissions=True, ignore_version=True)
	frappe.db.commit()

@frappe.whitelist()
def create_log(lead, fingerprint, session_id, page_info):
	existing_log = frappe.get_value('Website Visitors Log',filters={'session_id': session_id})
	if existing_log:
		log = frappe.get_doc("Website Visitors Log", existing_log, ignore_permissions=True)
		create_new_entry_in_child_table(log, page_info)
	else:
		ip = fingerprint.get("properties", {}).get("network_properties", {}).get("ip_address", {})
		city = fingerprint.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("city", {})
		country = fingerprint.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("country", {})
		region = fingerprint.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("region", {})

		log = frappe.get_doc({
			'doctype': 'Website Visitors Log',
			'email_id': lead.email_id,
			'lead': lead.name,
			'ip': ip,
			'city': city,
			'country': country,
			'region': region,
			'session_id': session_id,
			'visited_at': frappe.utils.now()
		})
		log.insert(ignore_permissions=True)
		frappe.db.commit()

		create_new_entry_in_child_table(log, page_info)
		update_on_website(lead)
		update_visitor_details(lead, fingerprint)

class WebsiteVisitorsLog(Document):
	@staticmethod
	def clear_old_logs(days=180):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Website Visitors Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

