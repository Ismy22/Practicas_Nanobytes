# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    operation_type_id = fields.Many2one('sii.operation.type', string=_("Operation Type"), domain=[('code', 'ilike', 'N')])
    cause_exemption_id = fields.Many2one('sii.cause.exemption', string=_("Cause Exemption"))
