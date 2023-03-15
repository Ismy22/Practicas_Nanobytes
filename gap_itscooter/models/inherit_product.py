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

    def create(self, vals):
        product = super(Product, self).create(vals)
        return product

    def create_products_from_csv():
        file_path = '/ruta/al/archivo.csv'
        with open(file_path) as csvfile:
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

                # Asegurarse de que Qty y EAN tengan valores predeterminados
                qty = qty or 0.0
                ean = ean or ''

                # Crear objeto de producto
                product = Products.create({
                    'sku': sku,
                    'ean': ean,
                    'name': name,
                    'price': float(price),
                    'qty': float(qty)
                })

                print(f'Creado producto {product.name} con SKU {product.sku}')
        

    