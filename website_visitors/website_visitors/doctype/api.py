import requests
import frappe
import tldextract
from frappe.utils import validate_email_address
from website_visitors.website_visitors.doctype.website_visitors_log.website_visitors_log import create_log

def get_fingerprint_details(telemetry_id):
    url = f"https://telemetry.stytch.com/v1/fingerprint/lookup"
    username = frappe.conf.stytch_project_id
    password = frappe.conf.stytch_secret
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "telemetry_id": telemetry_id
    }
    try:
        response = requests.post(url, auth=(username, password), headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def create_lead(fingerprint, email, form_data, script):
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
        lead.visitor_details = fingerprint
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
        lead.visit_count = 1
        lead.visitor_details = fingerprint
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
def handle_form_submission(telemetry_id, website_token, form_data):
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

    fingerprint = get_fingerprint_details(telemetry_id.get("telemetryId", {}))
    frappe.enqueue(
        method="website_visitors.website_visitors.doctype.api.save_form_submission",
        queue="default",
        is_async=True,
        fingerprint=fingerprint,
        form_data=form_data,
        script=script
    )

def save_activity(fingerprint=None, session_id=None, page_info=None, page_event=None, lead=None):
    if page_event == "Left Website Page":
        frappe.db.set_value("Lead", lead.name, "on_website", 0, update_modified=False)
        frappe.db.commit()
    if "page_close_time" in page_info and page_info["page_close_time"]:
        create_log(lead, fingerprint, session_id, page_info)

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

@frappe.whitelist(allow_guest=True)
def track_activity(telemetry_id, website_token, session_id, page_info, event):
    logger.info(f"Telemetry ID: {telemetry_id}, Website Token: {website_token}, Session ID: {session_id}, Page Info: {page_info}, Event: {event}")
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
    
    fingerprint = get_fingerprint_details(telemetry_id.get("telemetryId", {}))
    visitor_id = fingerprint.get('fingerprints', {}).get('visitor_id',{})
    query = """
        SELECT * FROM `tabLead`
        WHERE JSON_UNQUOTE(JSON_EXTRACT(visitor_details, '$.fingerprints.visitor_id')) = %s
    """
    lead = frappe.db.sql(query, (visitor_id,), as_dict=True)
    if not lead:
        return
    page_event = event
    frappe.enqueue(
        method="website_visitors.website_visitors.doctype.api.save_activity",
        queue="default",
        is_async=True,
        fingerprint=fingerprint,
        session_id=session_id,
        page_info=page_info,
        page_event=page_event,
        lead=lead[0]
    )
    