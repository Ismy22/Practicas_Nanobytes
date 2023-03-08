from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "sale.order"

    active = fields.Boolean(string="active", default=True)