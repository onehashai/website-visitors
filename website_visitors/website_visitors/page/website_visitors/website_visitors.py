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
            "city": visitor_details.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("city", {}),
            "country": visitor_details.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("country", {}),
            "region":  visitor_details.get("properties", {}).get("network_properties", {}).get("ip_geolocation", {}).get("region", {}),
            "ip_address": visitor_details.get("properties", {}).get("network_properties", {}).get("ip_address", {}),
            "email_id": lead["email_id"],
            "on_website": lead["on_website"],
        })
        
    return {"visitors": visitors}
