import frappe

def create_custom_fields():
    on_website = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Lead",
        "label": "On Website",
        "fieldname": "on_website",
        "fieldtype": "Check",
        "default": False,
        "hidden": True,
        "insert_after": "other_info_tab"
    })
    on_website.insert()
    on_website.save()

    visit_count = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Lead",
        "label": "Visit Count",
        "fieldname": "visit_count",
        "fieldtype": "Int",
        "default": 0,
        "hidden": True,
        "insert_after": "on_website"
    })
    visit_count.insert()
    visit_count.save()
    
    visitor_details = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Lead",
        "label": "Visitor Details",
        "fieldname": "visitor_details",
        "fieldtype": "JSON",
        "hidden": True,
        "insert_after": "visit_count"
    })
    visitor_details.insert()
    visitor_details.save()

def create_website_as_lead_source():
    lead_source = frappe.get_value('Lead Source', filters={'source_name': 'Website'})
    if not lead_source:
        doc = frappe.new_doc('Lead Source')
        doc.source_name = 'Website'
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

def create_lead_notification():
    notification_data = {
        "doctype": "Notification",
        "name": "New Lead Notification",
        "channel": "Email",
        "subject": "New Lead {{ doc.name }}",
        "event": "New",
        "document_type": "Lead",
        "send_system_notification": True,
        "condition": "doc.visitor_details",
        "recipients": [],
        "message": "New lead {{ doc.name }} has been created.",
    }
    
    notification = frappe.get_doc(notification_data)
    notification.insert()
    frappe.db.commit()

def lead_status_notification():
    notification_data = {
        "doctype": "Notification",
        "name": "Lead On Website Notification",
        "channel": "Email",
        "subject": "Lead On Website {{ doc.name }}",
        "event": "Value Change",
        "document_type": "Lead",
        "value_changed": "on_website",
        "send_system_notification": True,
        "condition": "doc.on_website",
        "recipients": [],
        "message": "Lead {{ doc.name }} is on Website.",
    }
    
    notification = frappe.get_doc(notification_data)
    notification.insert()
    frappe.db.commit()

def clear_website_visitors_log():
    doc = frappe.get_doc('Log Settings', 'Log Settings')
    doc.append("logs_to_clear", {
        "ref_doctype": "Website Visitors Log",
        "days": 90
    })
    doc.save()
    frappe.db.commit()

def after_install():
    create_custom_fields()
    create_website_as_lead_source()
    create_lead_notification()
    lead_status_notification()
    clear_website_visitors_log()