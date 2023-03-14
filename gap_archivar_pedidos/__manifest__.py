{
    'name': 'Gestión Gap Archivar',
    'sequence': -1003,
    'summary': '',
    'description': """ Gap archivar presupuestos""",
    'depends': ['sale_management', 'base', 'project'],
    'data': [
        'wizard/wizard_contactos_view.xml',
        'security/ir.model.access.csv',
        'views/view_inherit_presupuesto.xml',
        'views/view_inherit_search.xml',
        'views/view_wizard_form_inherit_contactos.xml',
    ],
    'auto_install': False,
    'application': True
}