from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.Many2one('res.users', string='Usuario')
    project = fields.Many2one('project.project', string='Proyecto', domain="[('user_id', 'in', partner_id.proyectos.ids)]")

    def save_contact_wizard(self):
        if not self.user or not self.project:
            raise ValidationError(_('Debe seleccionar un usuario y un proyecto.'))

        project_record = self.env['project.project'].search([('id', '=', self.project.id)])
        if project_record:
            project_record  
        else:
            raise ValidationError(_('Error al asignar el proyecto'))

        return {'type': 'ir.actions.act_window_close'}
    

    def get_user_projects(self):
        for r in self:
            if r.user:
                projects = self.env['project.project'].search([('user_id', '=', self.user.id)])
                r.project = projects.id
            else:
                r.project = False
