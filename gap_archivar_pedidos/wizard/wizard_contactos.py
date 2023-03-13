from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    use_id = fields.Many2one('res.users', string='Usuario',  compute="get_user_projects")
    project_id = fields.Many2one('project.project', string='Proyecto')


    def save_contact_wizard(self):
        
        if not self.user_id or not self.project_id:
            raise ValidationError(_('Debe seleccionar un usuario y un proyecto.'))

        project_record = self.env['project.project'].search([('id', '=', self.project_id.id)])
        if project_record:
            
            project_record  
        else:
            raise ValidationError(_('Error al asignar el proyecto'))

        return {'type': 'ir.actions.act_window_close'}
    

    def get_user_projects(self):
        logger.info(self.env.context)
        for r in self:
            r.user_id = 2
            projects_id = self.env['project.project'].search([('user_id', '=', 2)])


class Partner(models.Model):
    _inherit = "res.partner"

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('gap_archivar_pedidos.view_res_user_wizard_form').id
        return {
            'name': 'Reasignar proyecto',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.user.wizard',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_partner_id': 'active_id',
            }
        }

    
  