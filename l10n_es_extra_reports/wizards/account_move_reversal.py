# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    sii_rectificative_type = fields.Selection([('S', _('By substitution')), ('I', _('By differences'))], string=_("Rectificative Type"))

    def _prepare_default_reversal(self, move):
        result = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        result.update({'sii_rectificative_type': self.sii_rectificative_type or 'I'})
        return result
