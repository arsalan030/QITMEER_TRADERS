{
    'name': 'Sale Brand Pricelist',
    'version': '1.0.0',
    'summary': 'Auto-apply a customer-specific pricelist per product brand on sale orders',
    'description': """
Brand-based customer pricing
============================
* Adds Brands and a Brand field on products.
* Adds a "Brand Pricelists" tab on customers: one pricelist per brand.
* On sale order lines, the price is taken from the customer's pricelist
  for the product's brand. If none is set, the order's normal pricelist is used.
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
    ],
    'installable': True,
    'application': False,
}
