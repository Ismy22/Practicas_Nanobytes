from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Project(models.Model):
    _name = 'user.project'
    _description = 'User Project'
    
    name = fields.Char(string='Proyecto')
    user = fields.Many2one('res.users', string='Usuario')

class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.Many2one('res.users', string='Usuario')
    #project = fields.Many2one('project.project', string='Proyecto')
    project = fields.One2many('user.project', 'Usuario', string='Projects')
    # user = fields.Char(String='Usuario')
    # project = fields.Char(String='Proyecto')

    def save_contact_wizard(self):
        if not self.user or not self.project:
            raise ValidationError(_('Debe seleccionar un usuario y un proyecto.'))

        project_record = self.env['project.project'].search([('id', '=', self.project.id)])
        if project_record:
            project_record  
        else:
            raise ValidationError(_('Error al asignar el proyecto'))

        return {'type': 'ir.actions.act_window_close'}
    
    @api.onchange
    def _onchange_user(self):
        if self.user:
            self.project_ids = self.env['user.project'].search([('user_id', '=', self.user.id)])
        else:
            self.project_ids = False