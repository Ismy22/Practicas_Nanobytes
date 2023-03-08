from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    @api.multi
    def action_archive(self):
        res = super(AccountMove, self).action_archive()

        for line in self.order_line:
            line.action_cancel()

        return res