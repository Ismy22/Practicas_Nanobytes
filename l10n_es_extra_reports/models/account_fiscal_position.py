# -*- coding: utf-8 -*-

from odoo import fields, models, _

class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    is_dua = fields.Boolean(string="Is DUA?", default=False)
    sii_reg_key_sale_id = fields.Many2one('sii.reg.key', string=_('SII Registration Key for Sales'), domain=[('type', '=', 'sale')])
    sii_reg_key_purchase_id = fields.Many2one('sii.reg.key', string=_('SII Registration Key for Purchases'), domain=[('type', '=', 'purchase')])

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_sii_active = fields.Boolean(related='company_id.is_sii_active', string=_('Is SII active?'))
    is_dua = fields.Boolean(string=_("Is DUA?"), default=False)
    sii_reg_key_sale_id = fields.Many2one('sii.reg.key', string=_('SII Registration Key for Sales'), domain=[('type', '=', 'sale')])
    sii_reg_key_purchase_id = fields.Many2one('sii.reg.key', string=_('SII Registration Key for Purchases'), domain=[('type', '=', 'purchase')])
    sii_exempt_cause_id = fields.Many2one('sii.cause.exemption', string=_("SII Exempt Cause"))
    sii_partner_id_type = fields.Selection([('1', _('National')), ('2', _('Intracom')), ('3', _('Export'))], string=_("SII partner Id Type"))
    