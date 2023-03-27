from odoo import models, fields, api
from odoo import _, api, fields, models
from odoo.exceptions import UserError
       
class ReturnPicking(models.Model):
    _inherit = "stock.return.picking"

    location_id = fields.Many2one('stock.location', 'Return Location')





