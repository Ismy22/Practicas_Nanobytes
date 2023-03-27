from odoo import models, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'
    
    category_id = fields.Many2one('product.category', string="Category")


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def _create_valuation_layers(self, partner_id, qty_out, forced_quantity=None, valuation_date=None, layer_vals=None):
        res = super(StockMove, self)._create_valuation_layers(partner_id, qty_out, forced_quantity=forced_quantity, valuation_date=valuation_date, layer_vals=layer_vals)
        for layer in res:
            layer.category_id = layer.product_id.categ_id
        return res