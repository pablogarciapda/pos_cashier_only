# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_cashier_only = fields.Boolean(
        string='Es Cajero TPV',
        compute='_compute_is_cashier_only',
        search='_search_is_cashier_only',
        store=False,
    )
    is_admin = fields.Boolean(
        string='Es Administrador',
        compute='_compute_is_admin',
        store=False,
    )
    pos_config_ids = fields.Many2many(
        'pos.config',
        string='TPVs Asignados',
        compute='_compute_pos_config_ids',
        inverse='_inverse_pos_config_ids',
        store=False,
    )

    def _compute_is_cashier_only(self):
        cashier_group = self.env.ref(
            'pos_cashier_only.group_pos_cashier_only',
            raise_if_not_found=False,
        )
        if not cashier_group:
            for user in self:
                user.is_cashier_only = False
            return
        for user in self:
            user.is_cashier_only = cashier_group in user.group_ids

    def _compute_is_admin(self):
        for user in self:
            user.is_admin = user._is_admin() or user.login in ('admin', '__system__')

    def _compute_pos_config_ids(self):
        for user in self:
            employee = user.employee_id
            if not employee:
                user.pos_config_ids = self.env['pos.config']
                continue
            configs = self.env['pos.config'].sudo().search([
                '|', '|',
                ('basic_employee_ids', 'in', employee.id),
                ('minimal_employee_ids', 'in', employee.id),
                ('advanced_employee_ids', 'in', employee.id),
            ])
            user.pos_config_ids = configs

    def _inverse_pos_config_ids(self):
        for user in self:
            employee = user.employee_id
            if not employee:
                continue
            all_configs = self.env['pos.config'].sudo().search([])
            for config in all_configs:
                if config in user.pos_config_ids:
                    if employee not in config.advanced_employee_ids:
                        config.sudo().write({
                            'advanced_employee_ids': [(4, employee.id)],
                        })
                else:
                    if employee in config.advanced_employee_ids:
                        config.sudo().write({
                            'advanced_employee_ids': [(3, employee.id)],
                        })
                    if employee in config.basic_employee_ids:
                        config.sudo().write({
                            'basic_employee_ids': [(3, employee.id)],
                        })
                    if employee in config.minimal_employee_ids:
                        config.sudo().write({
                            'minimal_employee_ids': [(3, employee.id)],
                        })

    def _search_is_cashier_only(self, operator, value):
        cashier_group = self.env.ref(
            'pos_cashier_only.group_pos_cashier_only',
            raise_if_not_found=False,
        )
        if not cashier_group:
            return [('id', '=', False)]
        self.env.cr.execute(
            "SELECT uid FROM res_groups_users_rel WHERE gid = %s",
            [cashier_group.id],
        )
        cashier_user_ids = [row[0] for row in self.env.cr.fetchall()]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', cashier_user_ids)]
        else:
            return [('id', 'not in', cashier_user_ids)]

    def action_make_cashier(self):
        cashier_group = self.env.ref(
            'pos_cashier_only.group_pos_cashier_only',
            raise_if_not_found=False,
        )
        if not cashier_group:
            return
        for user in self:
            if cashier_group not in user.group_ids:
                user.write({'group_ids': [(4, cashier_group.id)]})
                if not user.employee_id:
                    user._create_employee_for_cashier()
        self._update_cashier_home_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cajeros TPV actualizados',
                'message': f'{len(self)} usuario(s) ahora son cajeros TPV',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_remove_cashier(self):
        cashier_group = self.env.ref(
            'pos_cashier_only.group_pos_cashier_only',
            raise_if_not_found=False,
        )
        if not cashier_group:
            return
        for user in self:
            if cashier_group in user.group_ids:
                user.write({'group_ids': [(3, cashier_group.id)]})
        self._update_cashier_home_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cajeros TPV actualizados',
                'message': f'{len(self)} usuario(s) ya no son cajeros TPV',
                'type': 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def _create_employee_for_cashier(self):
        self.ensure_one()
        if self.employee_id:
            return
        employee = self.env['hr.employee'].sudo().create({
            'name': self.name,
            'user_id': self.id,
            'company_id': self.env.company.id,
        })
        return employee

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if self.env.context.get('default_is_cashier_only'):
            cashier_group = self.env.ref(
                'pos_cashier_only.group_pos_cashier_only',
                raise_if_not_found=False,
            )
            if cashier_group:
                group_ids = defaults.get('group_ids', [])
                if (4, cashier_group.id) not in group_ids:
                    group_ids.append((4, cashier_group.id))
                defaults['group_ids'] = group_ids
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.is_cashier_only and not user.employee_id:
                user._create_employee_for_cashier()
        users._update_cashier_home_action()
        return users

    def write(self, vals):
        result = super().write(vals)
        if 'group_ids' in vals:
            self._update_cashier_home_action()
        return result

    def unlink(self):
        for user in self:
            if user.is_cashier_only:
                sessions = self.env['pos.session'].sudo().search([
                    ('user_id', '=', user.id),
                    ('state', '!=', 'closed'),
                ])
                if sessions:
                    raise UserError(_(
                        'No se puede eliminar el usuario "%s" porque tiene sesiones de TPV abiertas. '
                        'Cierre las sesiones primero o archive el usuario.',
                        user.name,
                    ))
        return super().unlink()

    def _update_cashier_home_action(self):
        cashier_group = self.env.ref(
            'pos_cashier_only.group_pos_cashier_only',
            raise_if_not_found=False,
        )
        if not cashier_group:
            return
        server_action = self.env.ref(
            'pos_cashier_only.action_open_pos_home',
            raise_if_not_found=False,
        )
        if not server_action:
            return
        for user in self:
            is_cashier = cashier_group in user.group_ids
            if is_cashier and user.action_id != server_action:
                super(ResUsers, user).write({'action_id': server_action.id})
            elif not is_cashier and user.action_id == server_action:
                super(ResUsers, user).write({'action_id': False})

    def _get_default_pos_config(self):
        return self.env['pos.config'].search(
            [('active', '=', True)], limit=1, order='id asc',
        )

    def action_open_pos_cashier(self):
        self.ensure_one()
        pos_config = self._get_default_pos_config()
        if not pos_config:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin TPV configurado',
                    'message': 'No hay ningún punto de venta activo.',
                    'type': 'warning',
                },
            }
        return pos_config.open_ui()
