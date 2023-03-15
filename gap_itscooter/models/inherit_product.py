from odoo import models, fields, api
import csv
import base64
import requests
import logging
logger = logging.getLogger(__name__)

class Products(models.Model):
    _inherit = "product.template"

    Qty = fields.Float(string="Cantidad total")
    Price_cost = fields.Float(string="Price")
    SKU = fields.Char(String='SKU')
    EAN = fields.Char(String='EAN')
    

class ProductImport(models.TransientModel):
    _name = 'product.import'

    

    @api.multi
    def import_products(self):
        url="https://www.gm2online.es/amfeed/feed/download?id=23&file=StockGm2.csv"
        response = requests.get(url)
        if response.ok:
            reader = csv.DictReader(response.content.decode('utf-8').splitlines())
            Product = self.env['product.product']
            for row in reader:
                vals = {
                    'SKU': row['SKU'],
                    'EAN': row['EAN'],
                    'name': row['Name'],
                    'Price_cost': row['Price'],
                    'QTY': row['QTY']
                }
                product = Product.create(vals)
            return {'type': 'ir.actions.act_window_close'}
        else:
            return {'type': 'ir.actions.act_window_close', 'warning': 'Unable to fetch data from URL.'}