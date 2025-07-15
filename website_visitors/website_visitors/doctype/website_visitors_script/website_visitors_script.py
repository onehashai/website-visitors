# Copyright (c) 2025, Rishabh Pandram and contributors
# For license information, please see license.txt

import frappe
import uuid
from frappe.model.document import Document

@frappe.whitelist()
def get_lead_fields():
    fields = frappe.get_meta("Lead").fields
    return [f.fieldname for f in fields if f.fieldname]

@frappe.whitelist()
def get_script_details(docname):
	base_url = "https://" + frappe.local.site
	web_visitor_script_dict = frappe.db.get_value("Website Visitors Script", docname, ["website_token", "use_mediator"], as_dict=True)
	if not web_visitor_script_dict:
		return False
    
	return {
        "base_url": base_url,
        "website_token": web_visitor_script_dict.website_token,
		"use_mediator": web_visitor_script_dict.use_mediator,
    }

@frappe.whitelist()
def generate_script(docname):
	doc = frappe.get_doc("Website Visitors Script", docname)
	if not doc.website_token:
		website_token = str(uuid.uuid4()).replace('-', '')
		doc.website_token = website_token
	doc.save()

class WebsiteVisitorsScript(Document):
	pass
