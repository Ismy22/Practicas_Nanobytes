from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class Saleorder(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="Active", default=True)

    # def action_archive(self):
    #     res = super(Saleorder, self).action_archive()
    #     for line in self.order_line:
    #         line.write({'active': False})
    #     return res
    
    # def action_unarchive(self):
    #     res = super(Saleorder, self).action_unarchive()

    #     for id in self:
    #         lineaPedido = self.env['sale.order.line'].search(domain=[('order_id', '=', id.id), ('active', '=', False)])
    #         for line in lineaPedido:
    #             line.write({'active': True})
    #         return res
       
class Saleorderline(models.Model):
    _inherit = "sale.order.line"

    #active = fields.Boolean(string="Active", related=Saleorder.active, default=True) #funciona
    active = fields.Boolean(string="Active", related='order_id.active', default=True) 


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def open_contact_wizard(self):
        wizard = self.env['contact.wizard'].create({})
        return {
            'name': 'Select User and Project',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.user.wizard',
            'target': 'new',
            'res_id': wizard.id,
        }
