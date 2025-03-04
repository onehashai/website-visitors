import requests
import json
import frappe
import tldextract
from frappe.utils import validate_email_address
from website_visitors.website_visitors.doctype.website_visitors_log.website_visitors_log import create_log, get_geolocation

def create_lead(fingerprint, email, form_data, script):
    visitor_id = fingerprint.get('visitorId', {})
    request_id = fingerprint.get('requestId', {})
    geolocation = get_geolocation(request_id)
    form_mapping_dict = {}
    for row in script.form_mapping:
        form_mapping_dict[row.name_attribute] = row.field_name

    existing_lead = frappe.get_value("Lead", filters={'email_id': email})
    if existing_lead:
        lead = frappe.get_doc("Lead", existing_lead, ignore_permissions=True)
        for key,value in form_data.items():
            if key in form_mapping_dict:
                setattr(lead, form_mapping_dict[key], value)

        lead.lead_owner = script.lead_owner
        visitor_details = lead.visitor_details
        if isinstance(visitor_details, str):
            visitor_details = json.loads(visitor_details)
    
        visitor_ids = visitor_details.get("visitor_id", [])
        if visitor_id not in visitor_ids:
            visitor_ids.append(visitor_id)
        visitor_details["visitor_id"] = visitor_ids

        lead.visitor_details = visitor_details
        lead.save(ignore_permissions=True)
    else:
        lead = frappe.get_doc({
            "doctype": "Lead",
            "email_id": email,
        })
        for key,value in form_data.items():
            if key in form_mapping_dict:
                setattr(lead, form_mapping_dict[key], value)

        lead.lead_owner = script.lead_owner
        lead.on_website = True
        lead.visit_count = 1
        visitor_details = {
            "geolocation": geolocation,
            "visitor_id": [visitor_id],
        }
        lead.visitor_details = visitor_details
        lead.save(ignore_permissions=True)
    frappe.db.commit()

def save_form_submission(fingerprint=None,form_data=None, script=None):
    email = None
    for key, value in form_data.items():
        if validate_email_address(str(value)):
            email = value
    if not email:
        frappe.log_error(f"Email in form is mandatory")
    
    if script.api_endpoint:
        payload = {
            "fingerprint": fingerprint,
            "form_data": form_data
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            requests.post(script.api_endpoint, json=payload, headers=headers)
        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Error sending data to api endpoint: {e}")
    else:
        create_lead(fingerprint, email, form_data, script)

@frappe.whitelist(allow_guest=True)
def handle_form_submission(fingerprint, website_token, form_data):
    request = frappe.local.request
    referer = request.headers.get("Referer")
    origin = request.headers.get("Origin")
    raw_url = origin or referer
    if raw_url:
        extracted = tldextract.extract(raw_url)
        domain = f"{extracted.domain}.{extracted.suffix}"
    else:
        domain = None

    script = frappe.get_doc("Website Visitors Script", {"website_token": website_token})
    if not script:
        return
    allowed_domains = [d.strip() for d in script.website_domain.split(",")]
    if domain is None or domain not in allowed_domains:
        return 

    frappe.enqueue(
        method="website_visitors.website_visitors.doctype.api.save_form_submission",
        queue="default",
        is_async=True,
        fingerprint=fingerprint,
        form_data=form_data,
        script=script
    )

def save_activity(fingerprint=None, session_id=None, page_info=None, event=None, lead=None):
    request_id = fingerprint.get('requestId', {})

    if event == "On Website Page":
        frappe.db.set_value("Lead", lead.name, "on_website", 1, update_modified=False)
    else:
        frappe.db.set_value("Lead", lead.name, "on_website", 0, update_modified=False)
    frappe.db.commit()
    if "page_close_time" in page_info and page_info["page_close_time"]:
        create_log(lead, request_id, session_id, page_info)

@frappe.whitelist(allow_guest=True)
def track_activity(fingerprint, website_token, session_id, page_info, event):
    request = frappe.local.request
    referer = request.headers.get("Referer")
    origin = request.headers.get("Origin")
    raw_url = origin or referer
    if raw_url:
        extracted = tldextract.extract(raw_url)
        domain = f"{extracted.domain}.{extracted.suffix}"
    else:
        domain = None

    script = frappe.get_doc("Website Visitors Script", {"website_token": website_token})
    if not script:
        return
    allowed_domains = [d.strip() for d in script.website_domain.split(",")]
    if domain is None or domain not in allowed_domains:
        return 
    
    visitor_id = fingerprint.get('visitorId', {})
    lead = frappe.db.get_list(
        "Lead",
        filters={"visitor_details": ['like', f'%{visitor_id}%']},
        fields=['*']
    )
    if not lead:
        return
    
    frappe.enqueue(
        method="website_visitors.website_visitors.doctype.api.save_activity",
        queue="default",
        is_async=True,
        fingerprint=fingerprint,
        session_id=session_id,
        page_info=page_info,
        event=event,
        lead=lead[0]
    )
    