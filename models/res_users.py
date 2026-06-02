from odoo import models, api, fields, _
from odoo.exceptions import UserError

GROUP_USER_XMLID = 'base.group_user'
GROUP_PORTAL_XMLID = 'base.group_portal'
CASHIER_GROUP_XMLID = 'pos_cashier_only.group_pos_cashier_only'


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

    def _get_cashier_group(self):
        return self.env.ref(CASHIER_GROUP_XMLID, raise_if_not_found=False)

    def _get_user_group(self):
        return self.env.ref(GROUP_USER_XMLID, raise_if_not_found=False)

    def _get_portal_group(self):
        return self.env.ref(GROUP_PORTAL_XMLID, raise_if_not_found=False)

    def _compute_is_cashier_only(self):
        cashier_group = self._get_cashier_group()
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
                    for field_name in ['advanced_employee_ids', 'basic_employee_ids', 'minimal_employee_ids']:
                        if employee in config[field_name]:
                            config.sudo().write({field_name: [(3, employee.id)]})

    def _search_is_cashier_only(self, operator, value):
        cashier_group = self._get_cashier_group()
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

    def _ensure_internal_user(self, user):
        user_group = self._get_user_group()
        portal_group = self._get_portal_group()
        if not user_group:
            return
        groups_to_add = []
        if user_group not in user.group_ids:
            groups_to_add.append((4, user_group.id))
        if portal_group and portal_group in user.group_ids:
            groups_to_add.append((3, portal_group.id))
        if groups_to_add:
            user.write({'group_ids': groups_to_add})

    def action_make_cashier(self):
        cashier_group = self._get_cashier_group()
        if not cashier_group:
            return
        for user in self:
            self._ensure_internal_user(user)
            if cashier_group not in user.group_ids:
                user.write({'group_ids': [(4, cashier_group.id)]})
            if not user.employee_id:
                user._create_employee_for_cashier()
        self._update_cashier_home_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_remove_cashier(self):
        cashier_group = self._get_cashier_group()
        if not cashier_group:
            return
        for user in self:
            if cashier_group in user.group_ids:
                user.write({'group_ids': [(3, cashier_group.id)]})
        self._update_cashier_home_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _create_employee_for_cashier(self):
        self.ensure_one()
        if self.employee_id:
            return self.employee_id
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
            cashier_group = self._get_cashier_group()
            user_group = self._get_user_group()
            if cashier_group and user_group:
                group_ids = defaults.get('group_ids', [])
                ids_to_add = [cashier_group.id, user_group.id]
                for group_id in ids_to_add:
                    if group_id not in group_ids and (4, group_id) not in group_ids:
                        group_ids.append((4, group_id))
                defaults['group_ids'] = group_ids
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        cashier_group = self._get_cashier_group()
        user_group = self._get_user_group()
        portal_group = self._get_portal_group()
        for vals in vals_list:
            if self.env.context.get('default_is_cashier_only') and cashier_group:
                group_ids = vals.get('group_ids', [])
                if isinstance(group_ids, list):
                    ids_to_add = [cashier_group.id]
                    if user_group:
                        ids_to_add.append(user_group.id)
                    for group_id in ids_to_add:
                        if group_id not in group_ids and (4, group_id) not in group_ids:
                            group_ids.append((4, group_id))
                    if portal_group and portal_group.id in group_ids:
                        group_ids.remove(portal_group.id)
                vals['group_ids'] = group_ids
        users = super().create(vals_list)
        for user in users:
            if cashier_group and cashier_group in user.group_ids and not user.employee_id:
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
            sessions = self.env['pos.session'].sudo().search([
                ('user_id', '=', user.id),
            ])
            if sessions:
                raise UserError(_(
                    'No se puede eliminar el usuario "%s" porque tiene sesiones de TPV '
                    'asociadas. Archive el usuario en su lugar.',
                    user.name,
                ))
            employee = user.employee_id
            if employee:
                employee.sudo().write({'user_id': False})
        return super().unlink()

    def _update_cashier_home_action(self):
        cashier_group = self._get_cashier_group()
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
