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

    def import_products(self):
        file_path = 'C:\Users\ismae\Downloads\StockGm2.csv'
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            Product = self.env['product.product']
            for row in reader:
                vals = {
                    'default_code': row['SKU'],
                    'barcode': row['EAN'],
                    'name': row['Name'],
                    'list_price': row['Price'],
                    'Qty': row['Qty']
                }
                product = Product.create(vals)
            return {'type': 'ir.actions.act_window_close'}
    

    