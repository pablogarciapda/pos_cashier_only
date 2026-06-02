from odoo import http, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def web_client(self, action_id=None, **kwargs):
        user = self.env.user
        if user and not user._is_public() and user.has_group('pos_cashier_only.group_pos_cashier_only'):
            return http.local_redirect('/pos/cashier/select')
        return super().web_client(action_id=action_id, **kwargs)
