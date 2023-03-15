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
        product = super(Products, self).create(vals)
        return product

    def create_products_from_csv():
        file_path = '/ruta/al/archivo.csv'
        with open(file_path) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                sku = row['SKU']
                ean = row['EAN']
                name = row['Name']
                qty = row['QTY']
                price = row['Price']                

                # Crear objeto de producto
                product = Products.create({
                    'sku': sku,
                    'ean': ean,
                    'name': name,
                    'qty': qty,
                    'price': price                    
                })

                print(f'Creado producto {product.name} con SKU {product.sku}')
    

    