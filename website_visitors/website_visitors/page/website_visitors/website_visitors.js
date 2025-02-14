frappe.pages['website-visitors'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Website Visitors',
		single_column: true
	});

	$(frappe.render_template("website_visitors")).appendTo(page.body.addClass("no-border"));
}