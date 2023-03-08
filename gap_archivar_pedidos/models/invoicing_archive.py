from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    active = fields.Boolean(string="active", default=True)