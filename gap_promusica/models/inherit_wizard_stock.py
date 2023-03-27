from odoo import models, fields, api
from odoo import _, api, fields, models
from odoo.exceptions import UserError
       
class ReturnPicking(models.Model):
    _inherit = "stock.return.picking"

    @api.model
    def default_get(self, fields):
        res = super(ReturnPicking, self).default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.picking':
            if len(self.env.context.get('active_ids', list())) > 1:
                raise UserError(_("You may only return one picking at a time."))
            picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
            if picking.exists():
                res.update({'picking_id': picking.id})
        return res

    picking_id = fields.Many2one('stock.picking')
    product_return_moves = fields.One2many('stock.return.picking.line', 'wizard_id', 'Moves')
    move_dest_exists = fields.Boolean('Chained Move Exists', readonly=True)
    original_location_id = fields.Many2one('stock.location')
    parent_location_id = fields.Many2one('stock.location')
    company_id = fields.Many2one(related='picking_id.company_id')
    location_id = fields.Many2one('stock.location', 'Return Location')





