# -*- coding: utf-8 -*-

import markupsafe

from odoo import models, fields, _
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)


class SpanishBookGoodInvestmentReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.book.es.gi.report.handler'
    _description = 'In invoice book report'
    _inherit = 'l10n_es.generic.book.es.report.handler'
