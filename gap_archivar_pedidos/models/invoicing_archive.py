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
        logger.info(orderlineid+ "= orderlineid")

        # query = "Update sale_order_line set active='True' where order_id = '"+orderid+"'
        # request.cr.execute(query)    
        # data = request.cr.fetchall() 

        for line in self.order_line:
            logger.info("line unarchive")
            logger.info(line)
            logger.info("fin line unarchive")
            line.write({'active': True})

        return res
    
    def write(self, vals):
        res = super(Saleorder, self).write(vals)
        logger.info("-----vals write-----")
        logger.info(vals)
        logger.info("fin vals write")
        if 'active' in vals and vals['active'] == True:
            for line in self.order_line:
                logger.info("line write")
                logger.info(line)
                logger.info("fin line write")
                if not line.active:
                    line.write({'active': True})
        return res
    
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    active = fields.Boolean(string="Active", default=True)
