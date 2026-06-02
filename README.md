# POS Cashier Only

Módulo para Odoo 19 que crea usuarios con rol de **cajero restringido**: solo pueden acceder al TPV (Punto de Venta), sin acceso al backend de Odoo.

## Autor

- **Pablo García Fernández**
- <https://github.com/pablogarciapda>

## Versión

19.0.1.1.0 · Licencia LGPL-3

## Dependencias

- `point_of_sale` — Terminal Punto de Venta
- `hr` — Empleados

## Funcionalidad

1. Grupo `Cajero TPV (solo caja)` que hereda de `base.group_user` + `point_of_sale.group_pos_manager`.
2. Creación autónoma: al crear un cajero se auto-crea un empleado vinculado.
3. Asignación a TPVs vía `advanced_employee_ids` (derechos avanzados: puede cerrar sesión).
4. Selector de TPV al login con tarjetas de los TPVs disponibles.
5. Bloqueo de backend vía `ir.rule` con `[('id', '=', 0)]` sobre `ir.ui.menu`.
6. Home Action que redirige al selector de TPV.
7. Protección al borrar si tiene sesiones asociadas (sugiere archivar).
8. Post-init hook que activa `module_pos_hr`.

## Instalación

1. Agregar al `addons_path` de Odoo.
2. Activar desde Aplicaciones → `POS Cashier Only`.
3. Ir a TPV → `Cajeros (acceso restringido)`.
4. Crear cajero y asignar TPVs.

## Licencia

LGPL-3
