from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)


class wizarResPartner(models.TransientModel):
    _name = 'res.user.wizard'
    _description = 'Wizard for change user/proyect'

    use_id = fields.Many2one('res.users', string='Usuario')
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
        logger.info('------------------------contact_id------------------------------')
        logger.info(contact_id)
        logger.info('------------------------FIN CONTACT_ID------------------------------')

        
        partner = self.env['res.users'].browse([('user_id', '=', contact_id)])
        logger.info('------------------------partner------------------------------')
        logger.info(partner)
        logger.info('------------------------FIN partner------------------------------')
        user_id = partner.user_id
        logger.info('------------------------user_id------------------------------')
        logger.info(user_id)
        logger.info('------------------------FIN USER_ID------------------------------')
        res.update({
            'user_id': partner,
        })
        
        return res


class Partner(models.Model):
    _inherit = "res.users"

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

    
  