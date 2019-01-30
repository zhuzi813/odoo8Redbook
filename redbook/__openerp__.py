# -*- coding: utf-8 -*-
{
    'name': "redbook",

    'summary': """
        Red book odoo connection.
        """,

    'description': """
        Red book Odoo Connection.
    """,

    'author': "Zhengyu Pan",
    'website': "http://",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product','sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
        'views.xml',
        'menu.xml',
        'product_view.xml',
        'so_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}
