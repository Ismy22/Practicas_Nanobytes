from odoo import fields, models

class ReturnPickinginherit(models.TransientModel):
    _inherit = 'stock.return.picking'

    location_id = fields.Many2one('stock.location', 'Return Location', domain="[]")

