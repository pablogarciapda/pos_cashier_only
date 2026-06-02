from odoo import http
from odoo.http import request


class CashierPosSelector(http.Controller):
    @http.route('/pos/cashier/select', type='http', auth='user', website=False)
    def select_pos(self, **kw):
        user = request.env.user
        if user._is_public() or not user.has_group('pos_cashier_only.group_pos_cashier_only'):
            return http.local_redirect('/web')

        employee = user.employee_id
        if employee:
            pos_configs = request.env['pos.config'].sudo().search([
                ('active', '=', True),
                ('advanced_employee_ids', 'in', employee.id),
            ])
        else:
            pos_configs = request.env['pos.config'].sudo().search([
                ('active', '=', True),
            ])

        if len(pos_configs) == 1:
            return self._redirect_to_pos(pos_configs)

        return request.render('pos_cashier_only.pos_selector_template', {
            'pos_configs': pos_configs,
            'user': user,
        })

    @http.route('/pos/cashier/open/<int:pos_id>', type='http', auth='user', website=False)
    def open_pos(self, pos_id, **kw):
        user = request.env.user
        if user._is_public() or not user.has_group('pos_cashier_only.group_pos_cashier_only'):
            return http.local_redirect('/web')

        pos_config = request.env['pos.config'].sudo().browse(pos_id)
        if not pos_config.exists():
            return http.local_redirect('/pos/cashier/select')

        return self._redirect_to_pos(pos_config)

    def _redirect_to_pos(self, config):
        return http.local_redirect(f'/pos/ui/{config.id}?from_backend=True')
