import frappe 
import json
from frappe.utils import datetime

def get_context(context):
    leads = frappe.db.get_list(
        'Lead',
        filters={'visitor_details': ['!=', '']},
        fields=['name', 'email_id', 'on_website', 'visitor_details'],
    )

    visitors = []
    for lead in leads:
        visitor_details = json.loads(lead["visitor_details"] or "{}")
        visitors.append({
            "city": visitor_details.get("geolocation", {}).get("city", {}).get("name", "N/A"),
            "country": visitor_details.get("geolocation", {}).get("country", {}).get("name", "N/A"),
            "country_code": visitor_details.get("geolocation", {}).get("country", {}).get("code", "N/A"),
            "email_id": lead["email_id"],
            "on_website": lead["on_website"],
        })
        
    return {"visitors": visitors}
