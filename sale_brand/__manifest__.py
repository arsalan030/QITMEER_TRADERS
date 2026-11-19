{
    'name': 'Sale Brand Pricelist',
    'version': '1.2.2',
    'summary': 'Auto-apply a customer-specific pricelist per product brand on sale orders',
    'description': """
Brand-based customer pricing
============================
* Adds Brands and a Brand field on products.
* Adds a "Brand Pricelists" tab on customers: one or more pricelists per brand.
* On sale order lines, the price is taken from the customer's pricelist
  for the product's brand. If none is set, the order's normal pricelist is used.
* If the product matches rules in several of the customer's pricelists,
  a wizard opens on the order line to pick which price rule to apply.
""",
    'category': 'Sales/Sales',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'product'],
    'data': [
        'security/ir.access.csv',
        'views/product_brand_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'wizard/sale_brand_rule_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_brand/static/src/js/sale_product_field_brand_rule.js',
        ],
    },
    'installable': True,
    'application': False,
}
