from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    user_id = fields.Many2one('res.users', string='Usuario')
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
    

    def default_get(self, fields):
        res = super(wizarResPartner, self).default_get(fields)
        contact_id = self._context.get('default_partner_id')
        user_por_partner = self.env['res.users'].search([('partner_id', '=', contact_id)])
        id_usuario = user_por_partner.id
        logger.info('------------id_usuario----------')
        logger.info(id_usuario)
        logger.info('------------FIN id_usuario----------')
        proyecto_por_usurario = self.env['project.project'].search([('user_id', '=', id_usuario)])

        # Actualización: filtrar proyectos por usuario actual
        proyecto_por_usurario = proyecto_por_usurario.filtered(lambda p: p.user_id == self.env.user)

        res.update({'user_id': user_por_partner,})
        res.update({'project_id': proyecto_por_usurario,})

        
        return res


class Partner(models.Model):
    _inherit = "res.partner"

    def action_open_delivery_wizard(self):
        logger.info(self.id)
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
                'default_partner_id': self.id,
            }
        }

    
  