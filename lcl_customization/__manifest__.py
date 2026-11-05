{
    'name': 'LCL Customization',
    'summary': 'Custom product pricelist enhancements',
    'description': """
        Customizations for product pricelists and pricing rules.
    """,

    'author': 'LCL | Ubaid-Ur-Rehman',
    'website': 'https://leaderscorp.net/',

    'category': 'Sales',
    'version': '20.0.1.0.0',

    'license': 'LGPL-3',

    'depends': [
        'base',
        'product',
        'sale_management',
    ],

    'data': [
        'views/product_pricelist_views.xml',
        'views/sale_order_view.xml',
    ],

    'installable': True,
    'application': False,
}