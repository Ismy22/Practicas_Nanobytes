from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    @api.multi
    def action_archive(self):
        # Llama a la función de archivar del modelo padre
        res = super(SaleOrder, self).action_archive()

        # Itera sobre todas las líneas de pedido y las archiva también
        for line in self.order_line:
            line.action_cancel()

        return res