from odoo import api, fields, models, _

class wizarResPartner(models.TransientModel):
    _name = 'res.partner.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.One2many('res.partner', string='Usuario')
    project = fields.Many2one('proyect.proyect', string='Proyecto')