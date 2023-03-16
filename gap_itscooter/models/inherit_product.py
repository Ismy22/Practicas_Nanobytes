from odoo import models, fields, api

import csv
import base64
from odoo.http import request
import requests
from io import StringIO
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


    def download_csv_file(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError("Failed to download CSV file from URL")
        
        # Obtiene la ruta absoluta de la carpeta Descargas
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        file_path = os.path.join(download_folder, "productos.csv")
        
        # Guarda el archivo CSV en la carpeta Descargas
        with open(file_path, "w", newline="") as csvfile:
            csvfile.write(response.content.decode("utf-8"))
      
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

        # Descargar el archivo CSV en la carpeta Descargas
        url = "/web/content/?model=product.template&id=33168&filename_export=products.csv&field=datas&download=true&filename=products.csv': No scheme supplied. Perhaps you meant http:///web/content/?model=product.template&id=33168&filename_export=products.csv&field=datas&download=true&filename=products.csv?".format(
                self._name,
                self.id,
            )
        self.download_csv_file(url)
        
        # Devolver un mensaje para confirmar la descarga del archivo CSV
        return {
            'name': 'Descarga de productos',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'message': 'El archivo CSV se ha descargado en la carpeta Descargas.'
            },
        }