from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if view_type == 'form':
            view_ref = 'mymodule.view_move_form_custom'
            view_id = self.env['ir.ui.view'].search([('name', '=', view_ref)]).id or view_id
        return super(AccountMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)