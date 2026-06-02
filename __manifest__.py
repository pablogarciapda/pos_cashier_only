# -*- coding: utf-8 -*-
{
    'name': 'POS Cashier Only',
    'version': '19.0.1.0.0',
    'summary': 'Crea usuarios cajeros que solo pueden acceder al TPV.',
    'description': """
        Este módulo permite crear usuarios con rol de cajero que:
        - Solo pueden acceder al TPV (Point of Sale)
        - No ven ningún menú del backend
        - Se redirigen automáticamente al TPV al iniciar sesión
        - No tienen acceso a configuración ni administración
        
        Características:
        - Grupo "Cajero TPV (solo caja)" con permisos completos sobre sesiones y pedidos
        - Redirección automática al TPV al intentar acceder al backend
        - Regla de menú que bloquea todos los menús del backend
        - Post-init hook que activa module_pos_hr automáticamente
    """,
    'author': 'Pablo García Fernández',
    'website': 'https://github.com/pablogarciapda',
    'category': 'Point of Sale',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'hr'],
    'data': [
        'security/pos_cashier_groups.xml',
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/pos_selector_template.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
