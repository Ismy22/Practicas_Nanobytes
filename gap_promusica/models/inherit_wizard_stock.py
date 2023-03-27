from odoo import models, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    
    category_id = fields.Many2one('product.category', string="Category")