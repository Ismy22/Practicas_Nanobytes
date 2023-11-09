# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SpanishMod390TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod390.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod390)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
