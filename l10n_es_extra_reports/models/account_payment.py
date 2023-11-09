# -*- coding: utf-8 -*-
from odoo import models, api, fields, _

METHOD_USED = [
    ('01', _("Transfer")),
    ('02', _("Check")),
    ('03', _("Is not recived/paid")),
    ('04', _("Other payment method")),
    ('05', _("Direct Debit"))
]

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    method_used = fields.Selection(string=_("Method Used"), selection=METHOD_USED, default='05', help=_("Used to identify method used for registry book"))
