from odoo import models, fields, api
import logging 

logger = logging.getLogger(__name__)

class Saleorder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    def action_archive(self):
        res = super(Saleorder, self).action_archive()
        logger.info(res)
        for line in self.order_line:
            logger.info(line)
            line.write({'active': False})

        return res
    
    def action_unarchive(self):
        res = super(Saleorder, self).action_unarchive()
        logger.info(res)
        for line in self.order_line:
            logger.info(line)
            line.write({'active': True})

        return res
    
    def write(self, vals):
        res = super(Saleorder, self).write(vals)
        logger.info(vals)
        if 'active' in vals and vals['active'] == True:
            for line in self.order_line:
                logger.info(line)
                if not line.active:
                    line.write({'active': True})
        return res
    
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    active = fields.Boolean(string="Active", default=True)
