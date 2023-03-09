from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

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
        lineaPedido = self.env['sale.order.line'].search(domain=[('order_id', '=', self.id), ('active', '=', False)], limit=1)
        for line in lineaPedido:
            logger.info("----------line en el for------------")
            logger.info(line)
            logger.info("----------fin line en el for---------")
            line.write({'active': True})
        return res
       
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    active = fields.Boolean(string="Active", default=True)
