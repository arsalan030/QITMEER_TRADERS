{
    'name': 'Custom Product Line Info',
    'version': '20.0.1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Add Internal Reference and Description to all document lines',
    'depends': ['sale', 'purchase', 'stock', 'account', 'mail'],
    'data': [

        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_move_views.xml',
        'views/account_move_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/multi_supplierinfo_views.xml',
        # 'views/internal_ref_note_views.xml',
        'data/mail_template_overdue.xml',
        'data/ir_cron_overdue.xml',
        'security/ir.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
