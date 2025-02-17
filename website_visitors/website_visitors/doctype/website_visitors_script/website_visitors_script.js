// Copyright (c) 2025, Rishabh Pandram and contributors
// For license information, please see license.txt

frappe.ui.form.on("Website Visitors Script", {
	refresh(frm) {
        frappe.call({
            method: "website_visitors.website_visitors.doctype.website_visitors_script.website_visitors_script.get_script_details",
            args: {
                docname: frm.doc.name,
            },
            callback: function (r) {
                if (r.message){
                    const htmlContent = `
                        <h3 style="margin-top:26px; ">Put it inside head tag of your web page</h3>
                        <div style="background-color: #f4f4f4; border-radius: 6px;padding: 8px">
                            <code>&lt;script&gt;
                                (function(d,t) {
                                    var BASE_URL="${r.message.base_url}";
                                    var websiteToken = "${r.message.website_token}";
                                    var g=d.createElement(t),s=d.getElementsByTagName(t)[0];
                                    g.src=BASE_URL+"/assets/website_visitors/js/website_visitor.js?token="+websiteToken;
                                    g.defer = true;
                                    g.async = true;
                                    s.parentNode.insertBefore(g,s);
                                })(document,"script");
                            &lt;/script&gt;</code>
                        </div>
                    `;
                    frm.set_df_property('script', 'options', htmlContent);
                    frm.set_df_property('example_request', 'description', `Domain: ${r.message.base_url}. Go to User list->Settings->API Access for generating key and secret`);
                }
            },

        });
	},

    validate: function (frm) {
        let domainRegex = /^(?!www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!domainRegex.test(frm.doc.website_domain)) {
            frappe.msgprint(__("Please enter a valid domain (e.g., example.com)"));
            frappe.validated = false;
            return;
        }
    },

    before_save(frm) {
        if (frm.doc.website_domain) {
            frm.doc.website_domain = frm.doc.website_domain.toLowerCase();
        }
    },

    after_save(frm){
        frappe.call({
            method: "website_visitors.website_visitors.doctype.website_visitors_script.website_visitors_script.generate_script",
            args: {
                docname: frm.doc.name,
            },
            callback: function (r) {
                frm.refresh()
            },
        });
    },

    onload(frm){
        frappe.call({
            method: "website_visitors.website_visitors.doctype.website_visitors_script.website_visitors_script.get_lead_fields",
            callback: function(r) {
                if (r.message) {
                    frm.fields_dict.form_mapping.grid.update_docfield_property(
                        "field_name",
                        "options",
                        r.message.join("\n")
                    )
                }
            }
        });
    }
});