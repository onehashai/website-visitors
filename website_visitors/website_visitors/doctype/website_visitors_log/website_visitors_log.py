# Copyright (c) 2025, Rishabh Pandram and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document

def get_geolocation(request_id):
    url = f"https://ap.api.fpjs.io/events/{request_id}?api_key={frappe.conf.fingerprint_secret_key}"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            geolocation = data.get("products", {}).get("ipInfo", {}).get("data", {}).get("v4", {}).get("geolocation", {})
            return geolocation
        else:
            frappe.log_error(f"Error fetching geolocation for request_id {request_id}: {response.status_code}")
            return None
    except Exception as e:
        frappe.log_error(f"Error: {e}")
        return None
	
def update_visitor_details(lead, geolocation):
	visitor_details = lead.visitor_details or {}

	if isinstance(visitor_details, str):
		visitor_details = json.loads(visitor_details)

	visitor_details["geolocation"] = geolocation
	# Convert back to JSON string before storing
	visitor_details_json = json.dumps(visitor_details)

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

@frappe.whitelist()
def create_log(lead, request_id, session_id, page_info):
	existing_log = frappe.get_value('Website Visitors Log',filters={'session_id': session_id})
	if existing_log:
		log = frappe.get_doc("Website Visitors Log", existing_log, ignore_permissions=True)
		create_new_entry_in_child_table(log, page_info)
	else:
		geolocation = get_geolocation(request_id)
		city = geolocation.get("city", {}).get("name", "N/A")
		country = geolocation.get("country", {}).get("name", "N/A")
		
		log = frappe.get_doc({
			'doctype': 'Website Visitors Log',
			'email_id': lead.email_id,
			'lead': lead.name,
			'city': city,
			'country': country,
			'session_id': session_id,
			'visited_at': frappe.utils.now()
		})
		log.insert(ignore_permissions=True)
		frappe.db.commit()

		create_new_entry_in_child_table(log, page_info)
		update_visitor_details(lead, geolocation)

class WebsiteVisitorsLog(Document):
	@staticmethod
	def clear_old_logs(days=180):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Website Visitors Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

