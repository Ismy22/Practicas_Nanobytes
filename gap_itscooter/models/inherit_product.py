from odoo import models, fields, api

import csv
import base64
import requests
import logging
logger = logging.getLogger(__name__)

class Products(models.Model):
    _inherit = "product.template"

    Qty = fields.Float(string="Cantidad total", default=0.0)
    Price_cost = fields.Float(string="Price", default=0.0)
    SKU = fields.Char(String='SKU')
    EAN = fields.Char(String='EAN')


    def create_products_from_csv(self):
        file_path = "/mnt/extra-addons/gap_itscooter/docs/StockGm2.csv"
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                SKU = row.get('SKU')
                EAN = row.get('EAN')
                name = row.get('Name')
                Price_cost = row.get('Price')
                Qty = row.get('Qty')

                if not SKU or not name or not Price_cost:
                    # Ignorar filas sin SKU, nombre o precio
                    continue


                # Crear producto
                vals = {
                    'SKU': SKU,
                    'EAN': EAN,
                    'name': name,
                    'Price_cost': float(Price_cost),
                    'Qty': float(Qty)
                }
                product = self.env['product.template'].create(vals)

                print(f'Creado producto {product.name} con SKU {product.SKU}')
        

    