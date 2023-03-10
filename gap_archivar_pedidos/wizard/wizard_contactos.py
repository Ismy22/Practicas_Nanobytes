from odoo import api, fields, models, _

class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.Many2one('res.partner', string='Usuario')
    project = fields.Many2one('proyect.proyect', string='Proyecto')

    def save_contact_wizard(self):
        return



