# -*- coding: utf-8 -*-
{
    'name': 'Spain - Accounting Extra Reports',
    'version': '16.0.1',
    'author': 'Nanobytes Informatica y Telecomunicaciones S.L',
    'website': 'https://nanobytes.es',
    'category': 'Accounting',
    'description': """
        Accounting reports for Spain
    """,
    "external_dependencies": {
        "python": ["zeep","requests"],
    },
    'depends': [
        'account', 
        'l10n_es', 
        #'l10n_es_reports', 
        #'account_asset', 
        #'account_accountant', 
        'product', 
        'account_chart_update', 
        'queue_job',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sii_models_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'views/account_fiscal_position_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'wizards/account_payment_register_views.xml',
        'wizards/account_move_reversal_views.xml',
        'wizards/sii_certificate_password_views.xml',
        'data/account_tax_data.xml',
        #'data/book_es_generic_report.xml',
        #'data/book_es_out_report.xml',
        #'data/book_es_in_report.xml',
        'data/sii_extra_tax_template_data.xml',
        'data/sii_data.xml',
        'data/sii_agency_data.xml',
        'data/sii_map_v1_data.xml',
        'data/sii_map_v1_1_data.xml',
        'data/account_fiscal_position_data.xml',
        #'data/mod180.xml',
        #'data/mod190.xml',
        #'data/mod303.xml',
        #'data/mod390.xml',
        'data/product_product_data.xml',
        'data/res_country_data.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OEEL-1',
    'post_init_hook': 'post_extra_reports_sequences',
}
