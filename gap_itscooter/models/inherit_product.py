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


    def create_products_from_csv(self):
        file_path = "/mnt/extra-addons/gap_itscooter/docs/StockGm2.csv"
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                sku = row.get('SKU')
                ean = row.get('EAN')
                name = row.get('Name')
                price = row.get('Price')
                qty = row.get('Qty')

                if not sku or not name or not price:
                    # Ignorar filas sin SKU, nombre o precio
                    continue

                # hacer que Qty y EAN tengan valores predeterminados
                qty = qty or 0.0
                ean = ean or ''

                # Crear producto
                vals = {
                    'default_code': sku,
                    'barcode': ean,
                    'name': name,
                    'list_price': float(price),
                    'qty_available': float(qty)
                }
                product = self.env['product.template'].create(vals)

                print(f'Creado producto {product.name} con SKU {product.sku}')
        

    