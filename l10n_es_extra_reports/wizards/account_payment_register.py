# -*- coding: utf-8 -*-
from odoo import models, api, fields, _

METHOD_USED = [
    ('01', "Transfer"),
    ('02', "Check"),
    ('03', "Is not recived/paid"),
    ('04', "Other payment method"),
    ('05', "Direct Debit")
]

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    method_used = fields.Selection(string=_("Method Used"), selection=METHOD_USED, default='05', help=_("Used to identify method used for registry book"))

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result=batch_result)
        payment_vals.update({'method_used': self.method_used})
        return payment_vals