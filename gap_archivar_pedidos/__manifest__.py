{
    'name': 'Gestión Gap Archivar',
    'sequence': -1003,
    'summary': '',
    'description': """ Gap archivar presupuestos""",
    'depends': ['sale_management'],
    'data': [
        'wizard/wizard_proyect'
        'views/view_inherit_presupuesto.xml',
        'views/view_inherit_search.xml',
        'views/view_user_form.xml',
    ],
    'auto_install': False,
    'application': True
}