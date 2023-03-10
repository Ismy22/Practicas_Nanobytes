from odoo import api, fields, models, _

class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.Many2one('res.partner', string='Usuario')
    project = fields.Many2one('proyect.proyect', string='Proyecto')


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def open_contact_wizard(self):
        wizard = self.env['res.user.wizard'].create({})
        return {
            'name': 'Select User and Project',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.user.wizard',
            'target': 'new',
            'res_id': wizard.id,
        }
    
    def save_contact_wizard(self):
        return