from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class Products(models.Model):
    _inherit = "product.template"

    Qty = fields.Integer(string="Cantidad total")
    

