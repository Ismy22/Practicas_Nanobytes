{
    'name': 'Gestión Gap Archivar',
    'sequence': -1003,
    'summary': '',
    'description': """ Gap archivar presupuestos""",
    'depends': ['sale_management'],
    'data': [
        'views/view_inherit_presupuesto.xml',
        'views/view_inherit_search.xml',
        'wizard/wizard_proyect'
    ],
    'auto_install': False,
    'application': True
}