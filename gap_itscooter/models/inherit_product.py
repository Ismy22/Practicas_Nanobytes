from odoo import models, fields, api

import csv
import base64
from odoo.http import request
import tempfile
import base64
import requests
from io import StringIO
from odoo.tools import config
from odoo.exceptions import UserError

import io
import os
import logging
logger = logging.getLogger(__name__)

class Products(models.Model):
    _inherit = "product.template"

    Qty = fields.Float(string="Cantidad total", default=0.0)
    Price_cost = fields.Float(string="Price", default=0.0)
    SKU = fields.Char(String='SKU')
    EAN = fields.Char(String='EAN')


    def create_products_from_csv(self):
        url = "https://www.gm2online.es/amfeed/feed/download?id=23&file=StockGm2.csv"
        response = requests.get(url)
        #si respuesta erronea
        if response.status_code != 200:
            raise ValueError("Failed to download CSV file from URL")

        file_contents = StringIO(response.content.decode("utf-8"))
        reader = csv.DictReader(file_contents)
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


    def export_products_to_csv(self):
        # Leer todos los productos
        products = self.search([])

        # Crear archivo CSV y escribir encabezados de columna
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(['SKU', 'EAN', 'Name', 'Price', 'Qty'])

        # Escribir cada producto en una fila
        for product in products:
            writer.writerow([product.SKU, product.EAN, product.name, product.Price_cost, product.Qty])

        # Codificar archivo CSV como base64
        csv_base64 = base64.b64encode(csv_data.getvalue().encode('utf-8'))

        # Crear un objeto ir.attachment para el archivo CSV
        attachment = self.env['ir.attachment'].create({
            'name': 'products.csv',
            'datas': csv_base64,
            'type': 'binary',
        })

        # Obtener la URL de descarga del archivo desde Odoo 
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/web/content/%s/%s/datas/%s' % (attachment._name, attachment.id, attachment.datas_fname)

        # Verificar si url es None
        if url is None:
            raise UserError("Error: 'web.base.url' no está configurado en el archivo de configuración de Odoo")

        # Devolver acción para descargar el archivo CSV
        return {
            'type': 'ir.actions.act_url',
            'url': url + '?download=true',
            'target': 'self',
        }