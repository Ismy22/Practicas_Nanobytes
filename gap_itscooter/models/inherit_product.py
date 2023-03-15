from odoo import models, fields, api
import logging
logger = logging.getLogger(__name__)

class Products(models.Model):
    _inherit = "product.template"

    Qty = fields.Integer(string="Cantidad total")
    Cost = fields.Monetary(string="Precio")
    SKU = fields.Char(String='SKU')
    EAN = fields.char(String='EAN')
    

