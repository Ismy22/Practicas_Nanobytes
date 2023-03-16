from odoo import models, fields, api

import csv
import base64
from odoo.http import request
from io import StringIO
import io
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

        
    def generate_product_csv(products):
        # Creamos un objeto para escribir en memoria
        output = io.StringIO()

        # Creamos un escritor CSV
        writer = csv.writer(output, delimiter=',', quotechar='"')

        # Escribimos la fila de encabezado
        writer.writerow(['Referencia Interna', 'Nombre', 'Descripción del sitio web', 'Precio', 'Stock', 'URL de la imagen'])

        # Escribimos una fila para cada producto
        for product in products:
            writer.writerow([product.default_code, product.name, product.website_description, product.list_price, product.qty_available, product.image_url])

        # Devolvemos el contenido del archivo CSV como una cadena de caracteres
        return output.getvalue()
    
   
    def generate_csv(self):
        # Obtenemos todos los productos
        products = self.env['product.template'].search([])

        # Generamos el archivo CSV
        csv_data = generate_product_csv(products)

        # Devolvemos el archivo CSV al usuario
        return request.make_response(csv_data, [('Content-Type', 'text/csv'), ('Content-Disposition', 'attachment; filename=products.csv')])
    