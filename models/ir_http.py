from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def web_client(self, action_id=None, **kwargs):
        return super().web_client(action_id=action_id, **kwargs)
