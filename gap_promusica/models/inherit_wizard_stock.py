from odoo import models, fields
       
class ReturnPicking(models.Model):
    _inherit = "stock.return.picking"

    location_id = fields.Many2one('stock.location', 'Return Location')





