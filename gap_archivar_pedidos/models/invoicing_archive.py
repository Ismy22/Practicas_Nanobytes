from odoo import models, fields, api

class Saleorder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    def action_archive(self):
        res = super(Saleorder, self).action_archive()

        for line in self.order_line:
            line.write({'active': False})

        return res
    
    def action_unarchive(self):
        res = super(Saleorder, self).action_unarchive()

        for line in self.order_line:
            line.write({'active': True})

        return res
    
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    active = fields.Boolean(string="Active", default=True)
