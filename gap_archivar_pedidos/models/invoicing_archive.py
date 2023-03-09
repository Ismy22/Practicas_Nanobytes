from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)

class Saleorder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    def action_archive(self):
        res = super(Saleorder, self).action_archive()
        logger.info("res archive")
        logger.info(res)
        logger.info("fin res archive")
        for line in self.order_line:
            logger.info("line archive")
            logger.info(line)
            logger.info("fin line archive")
            line.write({'active': False})

        return res
    
    def action_unarchive(self):
        res = super(Saleorder, self).action_unarchive()
        logger.info("res unarchive")
        logger.info(res)
        logger.info("fin res unarchive")
        
        orderlineid = self.id
        logger.info("-------------orderlineid-------------")
        logger.info(orderlineid)
        logger.info("-------------fin orderlineid-------------")

        lineaPedido = self.env['sale.order.line'].search(domain=
            [('order_id', '=', orderlineid), ('active', '=', False)])
        logger.info("line lineaPedido")
        logger.info(lineaPedido)
        logger.info("fin linePedido")

        for line in lineaPedido:
            logger.info("line unarchive")
            logger.info(line)
            logger.info("fin line unarchive")
            line.write({'active': True})

        return res
    
   
    
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    active = fields.Boolean(string="Active", default=True)
