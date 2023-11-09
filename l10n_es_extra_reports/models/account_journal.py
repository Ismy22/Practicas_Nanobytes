# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    activity = fields.Char(string=_("Activity"), help=_("To comply with articles 40.1, 47.2, 51 quater and 61.2 of the RIVA and article 9.4 of Order HAC/773/2019, the activity to which the entry corresponds will be distinguished. Used from move > journal > company. Example: A036533"))
    billing_agreement_registration = fields.Char(string=_("Billing Agreement Registration"), help=_("The authorization registration number (“RGE############”) obtained at the Agency's"))
    sii_summary_invoice = fields.Boolean(string=_("SII Summary Invoice"))
