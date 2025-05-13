{
    'name': 'Plannificateur Réapprovisionnement',
    'version': '15.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Module de planification de réapprovisionnement',
    'description': """
        Module pour la gestion et la planification du réapprovisionnement des stocks.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'stock',
        'purchase',
        'mrp',
        'product'
    ],
    'data': [
        'security/ir.model.access.xml',
        'views/menu_views.xml',
        'views/reapprovisionnement_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 