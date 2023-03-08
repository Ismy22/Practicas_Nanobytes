from odoo import models, fields, api

class Saleorder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    @api.multi
    def action_archive(self):
        res = super(Saleorder, self).action_archive()

        for line in self.order_line:
            line.action_cancel()

        return res