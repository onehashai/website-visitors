import requests
import json
import frappe
from website_visitors.website_visitors.doctype.website_visitors_log.website_visitors_log import create_log

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

def fingerprint_api_key(bootinfo):
    bootinfo.fingerprint_api_key = frappe.conf.fingerprint_api_key

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

@frappe.whitelist()
def create_lead_via_webhook():
    try:
        data = frappe.request.get_json()
        
        fingerprint = data.get("fingerprint", {})
        website_token = data.get("website_token", "")
        form_data = data.get("form_data", {})

        if not fingerprint:
            return {"status": "error", "message": "Missing fingerprint data"}
        if not website_token:
            return {"status": "error", "message": "Missing website_token"}
        if not form_data:
            return {"status": "error", "message": "Missing form_data"}
        
        email = form_data.get("email", "")
        if not email:
            return {"status": "error", "message": "email field in form is mandatory"}
        
        script = frappe.get_last_doc("Website Visitors Script", filters={'website_token': website_token})
        if not script:
            return {"status": "error", "message": "No website visitors script doc found for website_token"}

        create_lead(fingerprint, email, form_data)
        return {"status": "success", "message": "Lead created successfully"}
    except Exception as e:
        frappe.log_error(f"Error: {e}")
        return {"status": "error", "message": str(e)}

def create_lead(fingerprint, email, form_data):
    visitor_id = fingerprint.get('visitorId', {})
    request_id = fingerprint.get('requestId', {})
    geolocation = get_geolocation(request_id)

    existing_lead = frappe.get_value("Lead", filters={'email_id': email})
    if existing_lead:
        lead = frappe.get_doc("Lead", existing_lead, ignore_permissions=True)
        lead_meta = frappe.get_meta("Lead")
        lead_fields = [df.fieldname for df in lead_meta.fields]
        for key,value in form_data.items():
            if key in lead_fields:
                setattr(lead, key, value)
        
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
        lead_meta = frappe.get_meta("Lead")
        lead_fields = [df.fieldname for df in lead_meta.fields]
        for key,value in form_data.items():
            if key in lead_fields:
                setattr(lead, key, value)

        lead.on_website = True
        visitor_details = {
            "geolocation": geolocation,
            "visitor_id": [visitor_id],
        }
        lead.visitor_details = visitor_details
        lead.save(ignore_permissions=True)
    create_log(lead, geolocation)

@frappe.whitelist(allow_guest=True)
def handle_form_submission(fingerprint, website_token, form_data):
    logger.info(f"{fingerprint} {website_token} {form_data}")
    email = form_data.get('email', {})
    if not email:
        frappe.log_error(f"email field in form is mandatory")
    
    script = frappe.get_last_doc("Website Visitors Script", filters={'website_token': website_token})
    if not script:
        frappe.log_error(f"No website visitors script doc found for website_token: {website_token}")
    
    if script.api_endpoint:
        payload = {
            "fingerprint": fingerprint,
            "website_token": website_token,
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
        create_lead(fingerprint, email, form_data)

@frappe.whitelist(allow_guest=True)
def track_activity(fingerprint, website_token, event):
    logger.info(f"{event} {website_token} {fingerprint}")

    script = frappe.get_last_doc("Website Visitors Script", filters={'website_token': website_token})
    if not script:
        frappe.log_error(f"No website visitors script doc found for website_token: {website_token}")

    visitor_id = fingerprint.get('visitorId', {})
    request_id = fingerprint.get('requestId', {})
    
    lead = frappe.get_last_doc(
        'Lead',  
        filters={"visitor_details": ["like", f'%{visitor_id}%']}
    )

    if lead:
        visitor_details = lead.visitor_details or {}

        if isinstance(visitor_details, str):
            visitor_details = json.loads(visitor_details)

        if event == "On Website":
            lead.on_website = True
            geolocation = get_geolocation(request_id)
            visitor_details["geolocation"] = geolocation
            create_log(lead, geolocation)
        else :
            lead.on_website = False

        lead.save(ignore_permissions=True, ignore_version=True)
        