from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user = fields.Many2one('res.users', string='Usuario')
    project = fields.Many2one('project.project', string='Proyecto')

    def save_contact_wizard(self):
        if not self.user or not self.project:
            raise ValidationError(_('Debe seleccionar un usuario y un proyecto.'))

        project_record = self.env['project.project'].search([('id', '=', self.project.id)])
        logger.info('-------------------self.project----------')
        logger.info(project_record)
        logger.info('---------fin self.project-----------')
        if project_record:
            project_record  
        else:
            raise ValidationError(_('Error al asignar el proyecto'))

        return {'type': 'ir.actions.act_window_close'}
    

    def get_user_projects(self):
        for r in self:
            if self.user:
                projects = self.env['project.project'].search([('user_id', '=', self.user.id)])
                logger.info('-------------------project----------')
                logger.info(projects)
                logger.info('---------fin project-----------')
                self.project = projects.ids
                logger.info('-------------------self.project2----------')
                logger.info(self.project)
                logger.info('---------fin self.project2-----------')
            else:
                self.project = False
