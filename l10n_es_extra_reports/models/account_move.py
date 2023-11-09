# -*- coding: utf-8 -*-

import requests
import re

from datetime import datetime, date
from odoo import fields, models, api, _, exceptions

from odoo.exceptions import UserError, ValidationError

# Import logging
import logging
_logger = logging.getLogger(__name__)

# Import Zeep library
try:
    from zeep import Client
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
except (ImportError, IOError) as err:
    _logger.debug(err)

# Disable warnigs for requests
requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

# Import Queue Job decorator
try:
    from odoo.addons.queue_job.job import job
except ImportError:
    _logger.debug('Can not `import queue_job`.')
    import functools

    def empty_decorator_factory(*argv, **kwargs):
        return functools.partial
    job = empty_decorator_factory

# INFORMATION OF TYPE OF COMMUNICATIONS
#COMMUNICATIONS = {
#    "A0": "Alta de facturas/registro",
#    "A1": "Modificación de facturas/registros (errores registrales)",
#    "A4": "Modificación Factura Régimen de Viajeros",
#    "A5": "Alta de las devoluciones del IVA de viajeros",
#    "A6": "Modificación de las devoluciones del IVA de viajeros"
#}

RECONCILE = [
    ('1', _('Not verifiable')),
    ('2', _('In contrast process')),
    ('3', _('Not contrasted')),
    ('4', _('Partially contrasted')),
    ('5', _('Contrasted'))
]

SII_STATES = [
    ("not_sent", _("Not sent")),
    ("sent", _("Sent")),
    ("accepted_with_errors", _("Accepted with errors")),
    ("error", _("Error")),
    ("sent_modified", _("Registered in SII but last modifications not sent")),
    ("cancelled", _("Cancelled")),
    ("cancelled_modified", _("Cancelled in SII but last modifications not sent")),
]

CHECK_SII_CHANGED_FIELDS = [
    "state",
    "sii_reg_key_id",
    "line_ids",
    "sii_invoice_type_id",
    "l10n_es_reports_operation_date"
]

AUTO_IDENTIFY_FIELDS = [
    "state",
    "line_ids",
    "partner_id",
    "fiscal_position_id",
    "is_auto_identify"
]

SII_MOVE_TYPES = ['out_refund', 'out_invoice', 'in_refund', 'in_invoice']

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_default_sii_reg_key_id(self):
        key_obj = self.env['sii.reg.key']

        invoice_type = self.env.context.get('default_move_type')
        if invoice_type in ['in_invoice', 'in_refund']:
            key_obj = key_obj.search([('code', '=', '01'), ('type', '=', 'purchase')], limit=1)
        elif invoice_type in ['out_invoice', 'out_refund']:
            key_obj = key_obj.search([('code', '=', '01'), ('type', '=', 'sale')], limit=1)

        return key_obj and key_obj.id or False

    def _get_default_sii_invoice_type_id(self):
        type_obj = self.env['sii.invoice.type']

        invoice_type = self.env.context.get('default_move_type')
        if invoice_type in ['in_invoice', 'out_invoice']:
            type_obj = type_obj.search([('default', '=', True), ('type', '=', 'invoice')], limit=1)
        elif invoice_type in ['in_refund', 'out_refund']:
            type_obj = type_obj.search([('default', '=', True), ('type', '=', 'refund')], limit=1)

        return type_obj and type_obj or False

    def _get_default_sii_description(self):
        move_type = self.env.context.get('move_type', '')
        company = self.env.user.company_id
        description = '/'
        if not company.is_sii_description_automatic:
            if 'out_' in move_type:
                description = company.sii_description_sale or "/"
            if 'in_' in move_type:
                description = company.sii_description_purchase or "/"
            description += company.sii_description or ""
        return description

    @api.depends('invoice_line_ids')
    def _is_sii_available(self):
        for invoice in self:
            is_sii_available = False
            if invoice.is_sii_active and invoice.invoice_line_ids and invoice.move_type in SII_MOVE_TYPES:
                book = self.env['sii.map']._get_current_map()
                if book:
                    all_mapped_taxes = book._get_all_taxes('out_' in invoice.move_type and 'out' or 'in', exclude=['SRE'])
                    if all_mapped_taxes:
                        for line in invoice.invoice_line_ids:
                            for tax_line in line.tax_ids:
                                if tax_line.id in all_mapped_taxes.ids:
                                    is_sii_available = True
            invoice.is_sii_available = is_sii_available

    @api.depends('move_type')
    def _get_key_invoice_type(self):
        for r in self:
            if r.move_type in ['out_invoice', 'out_refund']:
                r.sii_key_invoice_type = 'sale'
            elif r.move_type in ['in_invoice', 'in_refund']:
                r.sii_key_invoice_type = 'purchase'
            else:
                r.sii_key_invoice_type = r.move_type

    is_auto_identify = fields.Boolean(string=_("Is auto identify?"), default=True, tracking=True, help=_("When this is active invoice type and is dua is auto calculated every write. Otherwise is configured by user."))
    sii_invoice_type_id = fields.Many2one('sii.invoice.type', string=_("Invoice Type"), default=lambda x: x._get_default_sii_invoice_type_id(), help="Invoice Type used for registry book or SII")
    is_dua = fields.Boolean(string="Is DUA?", default=False)    

    sii_reg_key_id = fields.Many2one('sii.reg.key', string=_("Registration key"), default=lambda x: x._get_default_sii_reg_key_id(), help="Registration key used for registry book or SII")
    l10n_es_reports_operation_date = fields.Date(string="Operation Date", help="Operation date used for registry book")
    sii_key_invoice_type = fields.Char(string="Key Invoice Type", compute="_get_key_invoice_type", store=True)
    sii_rectificative_type = fields.Selection([('S', 'By substitution'), ('I', 'By differences')], string="Rectificative Type")

    is_sii_active = fields.Boolean(related='company_id.is_sii_active', string='Is SII active?')
    sii_state = fields.Selection(SII_STATES, string="SII State", copy=False, readonly=True, default='not_sent', tracking=True)

    sii_error_message = fields.Text(string='SII Error', copy=False, readonly=True)

    sii_recc_sent = fields.Boolean(string='SII Payment RECC Sent', copy=False, readonly=True)
    sii_recc_csv = fields.Char(string='SII Payment RECC CSV', copy=False)
    sii_recc_result_ids = fields.One2many('sii.result', 'sii_move_id', string='Move RECC results', domain=[('sii_type', '=', 'recc')], copy=False, readonly=True)
    sii_recc_send_error = fields.Text(string='SII Payment RECC Send Error', copy=False, readonly=True)

    sii_csv = fields.Char(string='SII CSV', copy=False, tracking=True)
    sii_description = fields.Text(string='SII Description', default=lambda x: x._get_default_sii_description())
    sii_reconcile_state = fields.Selection(RECONCILE, string='Reconcile State', readonly=True)

    is_sii_available = fields.Boolean(string='Is available for SII?', compute='_is_sii_available', store=True)

    sii_first_invoice = fields.Many2one('account.move', string='SII First Invoice')

    sii_result_ids = fields.One2many('sii.result', 'sii_move_id', string='Move results', domain=[('sii_type', '=', 'normal')], copy=False)
    sii_check_result_ids = fields.One2many('sii.check.result', 'sii_move_id', string='Check results', copy=False)
    move_jobs_ids = fields.Many2many('queue.job', 'move_id', 'job_id', string="Move Jobs", copy=False)

    property_situations_id = fields.Many2one('sii.property.situation', string=_('Property Situation'), help="Property Situations used for registry book")
    cadastral_reference = fields.Char(string="Cadastral Reference")
    activity = fields.Char(string="Activity", help="To comply with articles 40.1, 47.2, 51 quater and 61.2 of the RIVA and article 9.4 of Order HAC/773/2019, the activity to which the entry corresponds will be distinguished. Used from move > journal > company. Example: A036533")
    later_deductible = fields.Boolean(string="Later Deductible", default=False)
    later_deductible_date = fields.Date(string="Later Deductible Date")

    @api.onchange('sii_rectificative_type')
    def onchange_sii_rectificative_type(self):
        if self.sii_rectificative_type == 'S' and not self.reversed_entry_id:
            self.sii_rectificative_type = False
            return {
                'warning': {
                    'message': _('You must have at least one original invoice linked to this one that will be substituted.')
                }
            }

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        self.onchange_fiscal_position()
        return res

    @api.onchange('fiscal_position_id')
    def onchange_fiscal_position(self):
        if self.fiscal_position_id and 'out_' in self.move_type:
            self.sii_reg_key_id = self.fiscal_position_id.sii_reg_key_sale_id
        elif self.fiscal_position_id and 'in_' in self.move_type:
            self.sii_reg_key_id = self.fiscal_position_id.sii_reg_key_purchase_id

    def _check_auto_identify(self):
        sii_map = self.env['sii.map']._get_current_map()
        invoice_type_obj = self.env['sii.invoice.type']
        for r in self:
            if r.is_auto_identify:
                is_dua = False
                sii_invoice_type_id = False

                if r.journal_id.sii_summary_invoice:
                        sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'F4')], limit=1).id
                else:
                    if r.fiscal_position_id.is_dua:
                        for line in r.line_ids.filtered(lambda x: x.tax_line_id):
                            dua_taxes = sii_map._get_group_taxes('in', ['SFRDUA'])
                            if line.tax_line_id.id in dua_taxes.ids:
                                is_dua = True


                    if is_dua and r.move_type not in ['out_refund', 'in_refund']:
                        sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'F5')], limit=1).id
                        if r.sii_reg_key_id and r.sii_reg_key_id.code == '13':
                            sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'F6')], limit=1).id
                    else:
                        if r.move_type in ['out_invoice', 'in_invoice']:
                            if r.partner_id.anonymous_customer and r.move_type in ['out_invoice']:
                                sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'F2')], limit=1).id
                            else:
                                sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'F1')], limit=1).id


                    if r.move_type in ['out_refund', 'in_refund']:
                        if r.partner_id.anonymous_customer and r.move_type in ['out_refund']:
                            sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'R5')], limit=1).id
                        else:
                            sii_invoice_type_id = invoice_type_obj.search([('code', '=', 'R4')], limit=1).id

                r.is_dua = is_dua
                if sii_invoice_type_id:
                    r.sii_invoice_type_id = sii_invoice_type_id

    def _check_aeat_data(self):
        for r in self:

            if not r.property_situations_id:
                if r.sii_reg_key_id and r.sii_reg_key_id.code in ['11', '12', '13']:
                    raise exceptions.ValidationError(_("When registration key is declared as 11, 12 or 13, property situations is mandatory!"))

                activity = r.activity or r.journal_id and r.journal_id.activity or r.company_id and r.company_id.activity or False
                if activity:
                    code_activity = activity[0:1]
                    type_activity = activity[1:3]

                    if str(code_activity+type_activity) == "A01":
                        raise exceptions.ValidationError(_("When activity code and type is declared as A01, property situations is mandatory!"))
                    elif str(code_activity) == "D":
                        raise exceptions.ValidationError(_("When activity code is declared as D, property situations is mandatory!"))

            if r.property_situations_id and r.property_situations_id.code in ['1', '2', '3'] and not r.cadastral_reference:
                raise exceptions.ValidationError(_("When situations code is declared as 1, 2 or 3, cadastral reference is mandatory!"))

    @api.onchange('invoice_line_ids')
    def _get_sii_description(self):
        description = '/'
        if "out_" in self.move_type:
            description = self.company_id.sii_description_sale or "/"
        if "in_" in self.move_type:
            description = self.company_id.sii_description_purchase or "/"
        if self.company_id.is_sii_description_automatic:
            for line in self.invoice_line_ids:
                description += (line.name or "") + ' - '
        self.sii_description = description

    @api.model_create_multi
    def create(self, vals_list):
        moves = super(AccountMove, self).create(vals_list)
        moves._check_aeat_data()

        for move, vals in zip(moves, vals_list):
            if any([True for field in AUTO_IDENTIFY_FIELDS if field in vals]):
                move._check_auto_identify()

        if any(not vals.get('sii_description', False) for vals in vals_list):
            for move in moves:
                move._get_sii_description()

        return moves

    def write(self, vals):

        for r in self:
            if 'partner_id' in vals:
                if r.sii_state == 'sent':
                    raise UserError(_("This invoice is sent to SII, if you change the partner you have to cancel it and drop the invoice from SII"))
            if ('name' in vals and r.move_type in ['out_invoice', 'out_refund']):
                if r.sii_state == 'sent' and vals['name'] != r.name:
                    raise UserError(_("This invoice is sent to SII, if you change the number you have to cancel it and drop the invoice from SII"))
            if ('ref' in vals and r.move_type in ['in_invoice', 'in_refund']):
                if r.sii_state == 'sent' and vals['ref'] != r.ref:
                    raise UserError(_("This invoice is sent to SII, if you change the number you have to cancel it and drop the invoice from SII"))
            if 'move_type' in vals:
                if r.sii_state == 'sent':
                    raise UserError(_("This invoice is sent to SII, if you change the type you have to cancel it and drop the invoice from SII"))
            if 'invoice_date' in vals:
                if r.sii_state == 'sent':
                    raise UserError(_("This invoice is sent to SII, if you change the date you have to cancel it and drop the invoice from SII"))

            if any([True for field in CHECK_SII_CHANGED_FIELDS if field in vals]):
                if r.sii_state == 'sent' or r.sii_state == 'accepted_with_errors':
                    vals.update({'sii_state': 'sent_modified'})
                if r.sii_state == 'cancelled':
                    vals.update({'sii_state': 'cancelled_modified'})


        res = super(AccountMove, self).write(vals)
        self._check_aeat_data()

        if any([True for field in AUTO_IDENTIFY_FIELDS if field in vals]):
            self._check_auto_identify()

        if not vals.get('sii_description', False):
            for move in self:
                move._get_sii_description()

        return res

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        if res:
            queue_obj = self.env['queue.job'].sudo()
            for r in self:
                if not r.l10n_es_reports_operation_date and r.invoice_date:
                    r.l10n_es_reports_operation_date = r.invoice_date
                if not r.sii_rectificative_type and r.move_type in ['out_refund', 'in_refund']:
                    r.sii_rectificative_type = 'I'

                if not r.move_jobs_ids.filtered(lambda x: x.state == 'pending') and r.sii_state == 'not_sent':
                    company = r.company_id
                    if company.is_sii_active and company.sii_send_moves_on == 'validate' and r.is_sii_available:
                        if not company.use_queue:
                            r._send_invoice_to_sii()
                        else:
                            eta = company._get_time()
                            new_delay = self.sudo().with_context(company_id=company.id).with_delay(eta=eta).confirm_one_invoice(r)
                            job = queue_obj.search([('uuid', '=', new_delay.uuid)], limit=1)
                            r.sudo().move_jobs_ids |= job

        return res

    @api.model
    def _get_tax_type(self, tax_line):
        if tax_line.amount_type == 'group':
            tax_type = abs(tax_line.children_tax_ids.filtered('amount')[:1].amount)
        else:
            tax_type = abs(tax_line.amount)
        return tax_type

    def _get_currency_rate_date(self):
        return self.date or self.invoice_date

    def _change_date_format(self, date):
        new_date = date.strftime('%d-%m-%Y')
        return new_date

    def _get_vat_number(self, vat_in):
        vat_out = vat_in
        if vat_in.startswith('ES'):
            vat_out = vat_in[2:]
        return vat_out

    def _get_country_code(self, vat):
        code = ''
        if vat:
            code = vat[:2]
            if code:
                country_id = self.env['res.country'].sudo().search([('code', '=', code)], limit=1)
                if country_id:
                    code = country_id.code
                else:
                    code = ''
        if not code:
            if self.partner_id.country_id:
                code = self.partner_id.country_id.code
        return code

    def _display_multiple_invoices_error(self):
        return _("You can't use this action for multiple invoices!")

    def _create_fail_activity(self):
        if self.company_id.sii_activity_type_id:
            if not self.activity_ids.filtered(lambda x: 'SII Error: ' in x.summary):
                model_id = self.env['ir.model'].search([('model', '=', 'account.move')])
                company = self.company_id
                user_id = self.user_id.id
                if company.sii_activity_user_id:
                    user_id = company.sii_activity_user_id.id
                date_deadline = fields.Date.today().strftime('%Y-%m-%d')
                activity_vals = {
                    'activity_type_id': company.sii_activity_type_id.id,
                    'res_id': self.id,
                    'res_model_id': model_id[0].id,
                    'date_deadline': date_deadline,
                    'user_id': user_id,
                    'summary': 'SII Error: ' + self.name,
                }
                self.env['mail.activity'].create(activity_vals)

    def _get_sii_gen_type(self):
        partner_ident = self.fiscal_position_id.sii_partner_id_type
        if partner_ident:
            res = int(partner_ident)
        elif self.fiscal_position_id.name == 'Régimen Intracomunitario':
            res = 2
        elif (self.fiscal_position_id.name ==
              'Régimen Extracomunitario / Canarias, Ceuta y Melilla') or (self.fiscal_position_id.name == "Régimen Extracomunitario"):
            res = 3
        else:
            res = 1
        return res

    def _get_line_price_subtotal(self, line):
        self.ensure_one()
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        return price

    def _get_tax_line_req(self, tax_type, line, line_taxes, invoice_type, sii_map):
        self.ensure_one()
        taxes = False
        taxes_re = sii_map._get_group_taxes(invoice_type, ['SRE'])
        if len(line_taxes) > 1:
            for tax in line_taxes:
                if tax in taxes_re:
                    price = self._get_line_price_subtotal(line)
                    taxes = tax.compute_all(price_unit=price, quantity=line.quantity, product=line.product_id, partner=line.move_id.partner_id)
                    taxes['percentage'] = tax.amount
                    return taxes
        return taxes

    def _get_sii_tax_line(self, tax_line, line, line_taxes, invoice_type, sii_map):
        self.ensure_one()
        tax_type = self._get_tax_type(tax_line)
        tax_line_req = self._get_tax_line_req(tax_type, line, line_taxes, invoice_type, sii_map)
        taxes = tax_line.compute_all(price_unit=self._get_line_price_subtotal(line), quantity=line.quantity, product=line.product_id, partner=line.move_id.partner_id)
        if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
            taxes_total = -taxes['total_excluded']
        else:
            taxes_total = taxes['total_excluded']
        taxes_amount = taxes['taxes'][0]['amount']
        if (self.currency_id !=
                self.company_id.currency_id):
            taxes_total = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(taxes_total, self.company_id.currency_id)
            taxes_amount = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(taxes['taxes'][0]['amount'], self.company_id.currency_id)
        tax_sii = {
            "TipoImpositivo": tax_type,
            "BaseImponible": taxes_total
        }
        if tax_line_req:
            tipo_recargo = tax_line_req['percentage']
            cuota_recargo = tax_line_req['taxes'][0]['amount']
            tax_sii['TipoRecargoEquivalencia'] = tipo_recargo
            tax_sii['CuotaRecargoEquivalencia'] = cuota_recargo

        if self.move_type in ['out_invoice', 'out_refund']:
            tax_sii['CuotaRepercutida'] = taxes_amount
        if self.move_type in ['in_invoice', 'in_refund']:
            tax_sii['CuotaSoportada'] = taxes_amount

            if tax_line in sii_map._get_group_taxes(invoice_type, ['SFRBI']):
                tax_sii['BienInversion'] = 'S'

        return tax_sii

    def _update_sii_tax_line(self, tax_sii, tax_line, line, line_taxes, invoice_type, sii_map):
        self.ensure_one()
        tax_type = self._get_tax_type(tax_line)
        tax_line_req = self._get_tax_line_req(tax_type, line, line_taxes, invoice_type, sii_map)
        taxes = tax_line.compute_all(price_unit=self._get_line_price_subtotal(line), quantity=line.quantity, product=line.product_id, partner=line.move_id.partner_id)
        if tax_line_req:
            cuota_recargo = tax_line_req['taxes'][0]['amount']
            tax_sii[str(tax_type)]['CuotaRecargoEquivalencia'] += cuota_recargo

        if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
            taxes_total = -taxes['total_excluded']
        else:
            taxes_total = taxes['total_excluded']
        taxes_amount = taxes['taxes'][0]['amount']
        if (self.currency_id !=
                self.company_id.currency_id):
            taxes_total = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(taxes_total, self.company_id.currency_id)
            taxes_amount = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(taxes['taxes'][0]['amount'], self.company_id.currency_id)
        tax_sii[str(tax_type)]['BaseImponible'] += taxes_total
        if self.move_type in ['out_invoice', 'out_refund']:
            tax_sii[str(tax_type)]['CuotaRepercutida'] += taxes_amount
        if self.move_type in ['in_invoice', 'in_refund']:
            tax_sii[str(tax_type)]['CuotaSoportada'] += taxes_amount

            if tax_line in sii_map._get_group_taxes(invoice_type, ['SFRBI']):
                tax_sii[str(tax_type)]['BienInversion'] = 'S'

        return tax_sii

    def _get_sii_exempt_cause(self, sii_map=False, invoice_type='', applied_groups=[]):
        # 1. Products
        product_exempt_causes = self.env['sii.cause.exemption']

        for group in applied_groups:
            product_exempt_causes |= self.mapped("invoice_line_ids").filtered(
                lambda x: (
                    any(tax in x.tax_ids for tax in group[0])
                    and x.product_id.cause_exemption_id
                )
            ).mapped("product_id.cause_exemption_id")

        if len(product_exempt_causes) > 1:
            raise exceptions.UserError(_("Currently there's no support for multiple exempt causes."))
        elif len(product_exempt_causes) == 1:
            return product_exempt_causes.code

        # 2. Fiscal position
        if self.fiscal_position_id and self.fiscal_position_id.sii_exempt_cause_id:
            return self.fiscal_position_id.sii_exempt_cause_id.code

        # 3. Map config
        if sii_map and applied_groups:
            for group in applied_groups:
                for line in self.invoice_line_ids:
                    if any(tax in line.tax_ids for tax in group[0]):
                        product_exempt_causes |= group[1]

        if len(product_exempt_causes) > 1:
            raise exceptions.UserError(_("Currently there's no support for multiple exempt causes."))
        elif len(product_exempt_causes) == 1:
            return product_exempt_causes.code

        # 4. Gen Type
        gen_type = self._get_sii_gen_type()
        if gen_type == 2:
            return "E5"
        elif gen_type == 3:
            return "E2"
        else:
            return False

    def _get_header(self, type_communication, sii_map):
        self.ensure_one()
        company = self.company_id
        if not company.vat:
            raise UserError(_("No VAT configured for the company '{}'").format(company.name))
        id_version_sii = sii_map.version
        vat = self._get_vat_number(self.company_id.vat)
        header = {
            "IDVersionSii": id_version_sii,
            "Titular": {
                "NombreRazon": self.company_id.name[0:120],
                "NIF": vat}
        }
        header['TipoComunicacion'] = type_communication
        return header

    def _connect_sii(self, wsdl):
        today = fields.Date.today()
        sii_config = self.env['sii.certificate'].search([
            ('company_id', '=', self.company_id.id),
            ('public_key', '!=', False),
            ('private_key', '!=', False),
            '|', ('date_start', '=', False),
            ('date_start', '<=', today),
            '|', ('date_end', '=', False),
            ('date_end', '>=', today),
            ('state', '=', 'active')
        ], limit=1)
        if sii_config:
            public_crt = sii_config.public_key
            private_key = sii_config.private_key
        else:
            public_crt = self.env['ir.config_parameter'].sudo().get_param('l10n_es_extra_reports.public_key', False)
            private_key = self.env['ir.config_parameter'].sudo().get_param('l10n_es_extra_reports.private_key', False)

        session = requests.Session()
        session.cert = (public_crt, private_key)
        transport = Transport(session=session)

        history = HistoryPlugin()

        return Client(wsdl=wsdl, transport=transport, plugins=[history])

    def _get_test_mode(self, port_name):
        if self.company_id.is_sii_test:
            port_name += 'Pruebas'
        return port_name

    def _connect_wsdl(self, wsdl, port_name):
        client = self._connect_sii(wsdl)
        port_name = self._get_test_mode(port_name)
        return client.bind('siiService', port_name)

    def _send_soap(self, wsdl, port_name, operation, param1, param2):
        serv = self._connect_wsdl(wsdl, port_name)
        return serv[operation](param1, param2)

    def _check_partner_vat(self):
        if not self.partner_id.anonymous_customer:
            if not self.partner_id.vat:
                raise UserError(_("The partner has not a VAT configured."))

    def _fix_country_code(self, dic_ret):
        if dic_ret['IDOtro']['CodigoPais'] == 'UK':
            dic_ret['IDOtro']['CodigoPais'] = 'GB'
        if dic_ret['IDOtro']['CodigoPais'] == 'RE':
            dic_ret['IDOtro']['CodigoPais'] = 'FR'
        if dic_ret['IDOtro']['CodigoPais'] == 'GP':
            dic_ret['IDOtro']['CodigoPais'] = 'FR'
        if dic_ret['IDOtro']['CodigoPais'] == 'MQ':
            dic_ret['IDOtro']['CodigoPais'] = 'FR'
        if dic_ret['IDOtro']['CodigoPais'] == 'GF':
            dic_ret['IDOtro']['CodigoPais'] = 'FR'

        return dic_ret

    def _get_sii_identifier(self):
        if self.partner_id.anonymous_customer or self.journal_id.sii_summary_invoice:
            return {}

        dic_ret = {}
        vat = ''.join(e for e in self.partner_id.vat if e.isalnum()).upper()
        nif = self._get_vat_number(vat)
        code = self._get_country_code(vat)
        document_type = self.partner_id.l10n_es_reports_documentation_type

        if document_type and code != "ES":
            dic_ret = {
                "IDOtro": {
                    "CodigoPais": code,
                    "IDType": document_type,
                    "ID": nif
                }
            }
            dic_ret = self._fix_country_code(dic_ret)
            return dic_ret
        else:
            if self.fiscal_position_id.name == 'Régimen Intracomunitario':
                dic_ret = {
                    "IDOtro": {
                        "CodigoPais": code,
                        "IDType": '02',
                        "ID": nif
                    }
                }
                dic_ret = self._fix_country_code(dic_ret)
            elif self.fiscal_position_id.name == 'Régimen Extracomunitario' or self.fiscal_position_id.name == \
                        'Régimen No sujeto por reglas de localización (TAI - Canarias, Ceuta, Melilla...)':
                dic_ret = {
                    "IDOtro": {
                        "CodigoPais": code,
                        "IDType": '04',
                        "ID": nif
                      }
                }
                dic_ret = self._fix_country_code(dic_ret)
            elif code == 'ES':
                dic_ret = {"NIF": nif}
            else:
                dic_ret = {
                    "IDOtro": {
                        "CodigoPais": code,
                        "IDType": '04',
                        "ID": nif
                      }
                }
        return dic_ret

    def _get_sii_out_taxes(self, sii_map):
        self.ensure_one()
        taxes_sii = {}
        taxes_f = {}
        taxes_to = {}

        # Sujetas
        taxes_sfesb, operation_sfesb, exemption_sfesb = sii_map._get_group('out', 'SFESB')
        taxes_sfess, operation_sfess, exemption_sfess = sii_map._get_group('out', 'SFESS')
        taxes_sfesisp, operation_sfesisp, exemption_sfesisp = sii_map._get_group('out', 'SFESISP')

        # No sujetas
        taxes_sfens, operation_sfens, exemption_sfens = sii_map._get_group('out', 'SFENS')
        taxes_sfesns, operation_sfesns, exemption_sfesns = sii_map._get_group('out', 'SFESNS')

        # Exentos
        taxes_sfesbe, operation_sfesbe, exemption_sfesbe = sii_map._get_group('out', 'SFESBE')
        taxes_sfesse, operation_sfesse, exemption_sfesse = sii_map._get_group('out', 'SFESSE')

        # Bienes exentos intra/extra
        taxes_sfesbei, operation_sfesbei, exemption_sfesbei = sii_map._get_group('out', 'SFESBEI')
        taxes_sfesbee, operation_sfesbee, exemption_sfesbee = sii_map._get_group('out', 'SFESBEE')

        groups_for_exemptions = [
            (taxes_sfesbe, exemption_sfesbe),
            (taxes_sfesse, exemption_sfesse),
            (taxes_sfesbei, exemption_sfesbei),
            (taxes_sfesbee, exemption_sfesbee),
        ]

        exempt_cause = self._get_sii_exempt_cause(sii_map=sii_map, invoice_type='out', applied_groups=groups_for_exemptions)

        # Invoice with not subject lines with 'DesgloseTipoOperacon' 
        identifier = self._get_sii_identifier()
        ns_dt = False
        if 'IDOtro' in identifier and self.sii_reg_key_id.code != '07':
            if identifier['IDOtro']['ID'][:3] != 'ESN':
                ns_dt = True

        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                if tax_line in taxes_sfesb or tax_line in taxes_sfesisp or tax_line in taxes_sfesbe or (tax_line in taxes_sfens and not ns_dt):
                    if 'DesgloseFactura' not in taxes_sii:
                        taxes_sii['DesgloseFactura'] = {}
                    inv_breakdown = taxes_sii['DesgloseFactura']
                    if tax_line in taxes_sfesb or tax_line in taxes_sfesbe or tax_line in taxes_sfesbee or tax_line in taxes_sfesisp:
                        if 'Sujeta' not in inv_breakdown:
                            inv_breakdown['Sujeta'] = {}
                        # TODO l10n_es no tiene impuesto exento de bienes
                        # corrientes nacionales
                        if tax_line in taxes_sfesbe:
                            price_subtotal = line.price_subtotal
                            if (self.currency_id != self.company_id.currency_id):
                                price_subtotal = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(price_subtotal, self.company_id.currency_id)
                            if 'Exenta' not in inv_breakdown['Sujeta']:
                                inv_breakdown['Sujeta']['Exenta'] = {}
                                inv_breakdown['Sujeta']['Exenta']['DetalleExenta'] = {'BaseImponible': price_subtotal}
                                if exempt_cause:
                                    inv_breakdown['Sujeta']['Exenta']['DetalleExenta'].update({'CausaExencion': exempt_cause})                                    
                            else:
                                inv_breakdown['Sujeta']['Exenta']['DetalleExenta']['BaseImponible'] += price_subtotal

                        if tax_line in taxes_sfesb or tax_line in taxes_sfesisp:
                            if 'NoExenta' not in inv_breakdown['Sujeta']:
                                inv_breakdown['Sujeta']['NoExenta'] = {}
                            if tax_line in taxes_sfesisp:
                                tipo_no_exenta = operation_sfesisp.code
                            else:
                                tipo_no_exenta = operation_sfesb.code
                            inv_breakdown['Sujeta']['NoExenta']['TipoNoExenta'] = tipo_no_exenta
                            if 'DesgloseIVA' not in inv_breakdown['Sujeta']['NoExenta']:
                                inv_breakdown['Sujeta']['NoExenta']['DesgloseIVA'] = {}
                                inv_breakdown['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] = []
                            tax_type = self._get_tax_type(tax_line)
                            if str(tax_type) not in taxes_f:
                                taxes_f[str(tax_type)] = self._get_sii_tax_line(tax_line, line, line.tax_ids, 'out', sii_map)
                            else:
                                taxes_f = self._update_sii_tax_line(taxes_f, tax_line, line, line.tax_ids, 'out', sii_map)

                    if tax_line in taxes_sfens and not ns_dt:
                        price_subtotal = line.price_subtotal
                        if (self.currency_id != self.company_id.currency_id):
                            price_subtotal = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(price_subtotal,self.company_id.currency_id)
                        if 'NoSujeta' not in inv_breakdown:
                            inv_breakdown['NoSujeta'] = {}
                        if line.product_id.sii_not_subject_7_14:
                            if 'ImportePorArticulos7_14_Otros' not in inv_breakdown['NoSujeta']:
                                inv_breakdown['NoSujeta'] = {'ImportePorArticulos7_14_Otros': price_subtotal}
                            else:
                                inv_breakdown['NoSujeta']['ImportePorArticulos7_14_Otros'] += price_subtotal
                        else:
                            if 'ImporteTAIReglasLocalizacion' not in inv_breakdown['NoSujeta']:
                                inv_breakdown['NoSujeta'] = {'ImporteTAIReglasLocalizacion': price_subtotal}
                            else:
                                inv_breakdown['NoSujeta']['ImporteTAIReglasLocalizacion'] += price_subtotal

                if tax_line in taxes_sfess or tax_line in taxes_sfesse or \
                    tax_line in taxes_sfesbee or tax_line in taxes_sfesbei or \
                        tax_line in taxes_sfesns or (tax_line in taxes_sfens and ns_dt):
                    if 'DesgloseTipoOperacion' not in taxes_sii:
                        taxes_sii['DesgloseTipoOperacion'] = {}
                    type_breakdown = taxes_sii['DesgloseTipoOperacion']
                    if tax_line in taxes_sfess or tax_line in taxes_sfesse or tax_line in taxes_sfesns:
                        if 'PrestacionServicios' not in type_breakdown:
                            type_breakdown['PrestacionServicios'] = {}
                        op_key = 'PrestacionServicios'
                    if tax_line in taxes_sfesbee or tax_line in taxes_sfesbei or (tax_line in taxes_sfens and ns_dt):
                        if 'Entrega' not in type_breakdown:
                            type_breakdown['Entrega'] = {}
                        op_key = 'Entrega'
                    if tax_line in taxes_sfesns or (tax_line in taxes_sfens and ns_dt):
                        price_subtotal = line.price_subtotal
                        if (self.currency_id != self.company_id.currency_id):
                            price_subtotal = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(price_subtotal, self.company_id.currency_id)
                        if 'NoSujeta' not in type_breakdown[op_key]:
                            type_breakdown[op_key]['NoSujeta'] = {}
                        if line.product_id.operation_type_id and line.product_id.operation_type_id.code == 'N1':
                            if 'ImportePorArticulos7_14_Otros' not in type_breakdown[op_key]['NoSujeta']:
                                type_breakdown[op_key]['NoSujeta'] = {'ImportePorArticulos7_14_Otros': price_subtotal}
                            else:
                                type_breakdown[op_key]['NoSujeta']['ImportePorArticulos7_14_Otros'] += price_subtotal
                        else:
                            if 'ImporteTAIReglasLocalizacion' not in type_breakdown[op_key]['NoSujeta']:
                                type_breakdown[op_key]['NoSujeta'] = {'ImporteTAIReglasLocalizacion': price_subtotal}
                            else:
                                type_breakdown[op_key]['NoSujeta']['ImporteTAIReglasLocalizacion'] += price_subtotal                                    
                    else:
                        if 'Sujeta' not in type_breakdown[op_key]:
                            type_breakdown[op_key]['Sujeta'] = {}

                    if tax_line in taxes_sfesse or tax_line in taxes_sfesbee or tax_line in taxes_sfesbei:
                        if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
                            price_subtotal = -line.price_subtotal
                        else:
                            price_subtotal = line.price_subtotal
                        if (self.currency_id != self.company_id.currency_id):
                            price_subtotal = self.currency_id.with_context(date=self._get_currency_rate_date()).compute(price_subtotal, self.company_id.currency_id)
                        if 'Exenta' not in type_breakdown[op_key]['Sujeta']:
                            type_breakdown[op_key]['Sujeta']['Exenta'] = {}
                            type_breakdown[op_key]['Sujeta']['Exenta']['DetalleExenta'] = {'BaseImponible': price_subtotal}
                            if tax_line in taxes_sfesbee:
                                type_breakdown[op_key]['Sujeta']['Exenta']['DetalleExenta']['CausaExencion'] = exempt_cause
                            if tax_line in taxes_sfesbei:
                                type_breakdown[op_key]['Sujeta']['Exenta']['DetalleExenta']['CausaExencion'] = exempt_cause
                        else:
                            type_breakdown[op_key]['Sujeta']['Exenta']['DetalleExenta']['BaseImponible'] += price_subtotal
                    if tax_line in taxes_sfesse:
                        if exempt_cause:
                            type_breakdown[op_key]['Sujeta']['Exenta']['DetalleExenta'].update({'CausaExencion': exempt_cause})
                    if tax_line in taxes_sfess:
                        if 'NoExenta' not in type_breakdown['PrestacionServicios']['Sujeta']:
                            type_breakdown['PrestacionServicios']['Sujeta']['NoExenta'] = {}
                            # TODO l10n_es_ no tiene impuesto ISP de servicios
                            # if tax_line in taxes_sfesisps:
                            #     TipoNoExenta = 'S2'
                            # else:
                            tipo_no_exenta = operation_sfess.code
                            type_breakdown[
                                'PrestacionServicios']['Sujeta']['NoExenta']['TipoNoExenta'] = tipo_no_exenta
                        if 'DesgloseIVA' not in taxes_sii['DesgloseTipoOperacion']['PrestacionServicios']['Sujeta']['NoExenta']:
                            type_breakdown['PrestacionServicios']['Sujeta']['NoExenta']['DesgloseIVA'] = {}
                            type_breakdown['PrestacionServicios']['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] = []
                        tax_type = self._get_tax_type(tax_line)
                        if str(tax_type) not in taxes_to:
                            taxes_to[str(tax_type)] = self._get_sii_tax_line(tax_line, line, line.tax_ids, 'out', sii_map)
                        else:
                            taxes_to = self._update_sii_tax_line(taxes_to, tax_line, line, line.tax_ids, 'out', sii_map)
        if len(taxes_f) > 0:
            for key, line in list(taxes_f.items()):
                if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = -round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaRepercutida', False):
                        line['CuotaRepercutida'] = -round(line['CuotaRepercutida'], 2)
                else:
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaRepercutida', False):
                        line['CuotaRepercutida'] = round(line['CuotaRepercutida'], 2)
                line['BaseImponible'] = round(line['BaseImponible'], 2)
                if line.get('TipoImpositivo', False):
                    line['TipoImpositivo'] = round(line['TipoImpositivo'], 2)
                taxes_sii['DesgloseFactura']['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'].append(line)
        if len(taxes_to) > 0:
            for key, line in list(taxes_to.items()):
                if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = -round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaRepercutida', False):
                        line['CuotaRepercutida'] = -round(line['CuotaRepercutida'], 2)
                else:
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaRepercutida', False):
                        line['CuotaRepercutida'] = round(line['CuotaRepercutida'], 2)
                line['BaseImponible'] = round(line['BaseImponible'], 2)
                taxes_sii['DesgloseTipoOperacion']['PrestacionServicios']['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'].append(line)
        if 'DesgloseFactura' in taxes_sii:
            t_key = 'DesgloseFactura'
            if 'NoSujeta' in taxes_sii[t_key]:
                if 'ImportePorArticulos7_14_Otros' in taxes_sii[t_key]['NoSujeta']:
                    ns_key = 'ImportePorArticulos7_14_Otros'
                else:
                    ns_key = 'ImporteTAIReglasLocalizacion'
                taxes_sii[t_key]['NoSujeta'][ns_key] = round(taxes_sii[t_key]['NoSujeta'][ns_key], 2)
                    
        if 'DesgloseTipoOperacion' in taxes_sii:
            t_key = 'DesgloseTipoOperacion'
            if 'Entrega' in taxes_sii[t_key] or 'PrestacionServicios' in taxes_sii[t_key]:
                if 'Entrega' in taxes_sii[t_key]:
                    dt_key = 'Entrega'
                else:
                    dt_key = 'PrestacionServicios'
                if 'Sujeta' in taxes_sii[t_key][dt_key]:
                    if 'Exenta' in taxes_sii[t_key][dt_key]['Sujeta']:
                        if 'DetalleExenta' in taxes_sii[t_key][dt_key]['Sujeta']['Exenta']:
                            if 'BaseImponible' in taxes_sii[t_key][dt_key]['Sujeta']['Exenta']['DetalleExenta']:
                                taxes_sii[t_key][dt_key]['Sujeta']['Exenta']['DetalleExenta']['BaseImponible'] = round(taxes_sii[t_key][dt_key]['Sujeta']['Exenta']['DetalleExenta']['BaseImponible'], 2)
                if 'NoSujeta' in taxes_sii[t_key][dt_key]:
                    if 'ImportePorArticulos7_14_Otros' in taxes_sii[t_key][dt_key]['NoSujeta']:
                        ns_key = 'ImportePorArticulos7_14_Otros'
                    else:
                        ns_key = 'ImporteTAIReglasLocalizacion'
                    taxes_sii[t_key][dt_key]['NoSujeta'][ns_key] = round(taxes_sii[t_key][dt_key]['NoSujeta'][ns_key], 2)
        if 'DesgloseTipoOperacion' in taxes_sii and 'DesgloseFactura' in taxes_sii:
            taxes_sii['DesgloseTipoOperacion']['Entrega'] = taxes_sii['DesgloseFactura']
            del taxes_sii['DesgloseFactura']
        
        return taxes_sii

    def _get_sii_in_taxes(self, sii_map):
        self.ensure_one()

        taxes_sii = {}
        taxes_f = {}
        taxes_isp = {}

        taxes_sfrs = sii_map._get_group_taxes('in', ['SFRS'])
        taxes_sfrisp = sii_map._get_group_taxes('in', ['SFRISP'])
        taxes_irpf = sii_map._get_group_taxes('in', ['SEFR'])
        taxes_nd = sii_map._get_group_taxes('in', ['SFRND'])
        taxes_ie = sii_map._get_group_taxes('in', ['SEIE'])

        no_deducible = False
        for line in self.invoice_line_ids:
            for tax_line in line.tax_ids:
                if tax_line in taxes_sfrs or tax_line in taxes_sfrisp or tax_line in taxes_nd or tax_line in taxes_ie:
                    if tax_line in taxes_sfrisp:
                        if 'InversionSujetoPasivo' not in taxes_sii:
                            taxes_sii['InversionSujetoPasivo'] = {}
                            taxes_sii['InversionSujetoPasivo']['DetalleIVA'] = []
                        tax_type = self._get_tax_type(tax_line)
                        if str(tax_type) not in taxes_isp:
                            taxes_isp[str(tax_type)] = self._get_sii_tax_line(tax_line, line, line.tax_ids, 'in', sii_map)
                        else:
                            taxes_isp = self._update_sii_tax_line(taxes_isp, tax_line, line, line.tax_ids, 'in', sii_map)
                    else:
                        if 'DesgloseIVA' not in taxes_sii:
                            taxes_sii['DesgloseIVA'] = {}
                            taxes_sii['DesgloseIVA']['DetalleIVA'] = []
                        tax_type = self._get_tax_type(tax_line)
                        if str(tax_type) not in taxes_f:
                            taxes_f[str(tax_type)] = self._get_sii_tax_line(tax_line, line, line.tax_ids, 'in', sii_map)
                        else:
                            taxes_f = self._update_sii_tax_line(taxes_f, tax_line, line, line.tax_ids, 'in', sii_map)
        if len(taxes_f) > 0:
            for key, line in list(taxes_f.items()):
                if self.move_type == 'in_refund' and self.sii_rectificative_type == 'I':
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = -round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaSoportada', False):
                        line['CuotaSoportada'] = -round(line['CuotaSoportada'], 2)
                    line['BaseImponible'] = -round(line['BaseImponible'], 2)
                else:
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaSoportada', False):
                        line['CuotaSoportada'] = abs(round(line['CuotaSoportada'], 2))
                    line['BaseImponible'] = round(line['BaseImponible'], 2)
                if line.get('TipoImpositivo', False):
                    line['TipoImpositivo'] = round(line['TipoImpositivo'], 2)
                taxes_sii['DesgloseIVA']['DetalleIVA'].append(line)
        if len(taxes_isp) > 0:
            for key, line in list(taxes_isp.items()):
                if self.move_type == 'in_refund' and self.sii_rectificative_type == 'I':
                    if line.get('CuotaRecargoEquivalencia', False):
                        line['CuotaRecargoEquivalencia'] = -round(line['CuotaRecargoEquivalencia'], 2)
                    if line.get('CuotaSoportada', False):
                        line['CuotaSoportada'] = -round(line['CuotaSoportada'], 2)
                    line['BaseImponible'] = -round(line['BaseImponible'], 2)
                else:
                    if line.get('CuotaSoportada', False):
                        line['CuotaSoportada'] = round(line['CuotaSoportada'], 2)
                    line['BaseImponible'] = round(line['BaseImponible'], 2)
                if line.get('TipoImpositivo', False):
                    line['TipoImpositivo'] = round(line['TipoImpositivo'], 2)
                taxes_sii['InversionSujetoPasivo']['DetalleIVA'].append(line)
        return taxes_sii

    def _get_invoices(self, sii_map=False):
        if not sii_map:
            sii_map = self.env['sii.map']._get_current_map()
        self._check_partner_vat()
        invoice_date = self._change_date_format(self.invoice_date)
        company = self.company_id
        ejercicio = fields.Date.from_string(self.date).year
        periodo = '%02d' % fields.Date.from_string(self.date).month
        if not self.sii_reg_key_id:
            raise UserError(_('You have to select a registration key in AEAT Tab.'))
        key = self.sii_reg_key_id.code
        if not self.sii_invoice_type_id:
            raise UserError(_('You have to select a invoice type in AEAT Tab.'))
        invoice_type = self.sii_invoice_type_id.code
        if not self.is_dua:
            if self.partner_id.is_company:
                nombrerazon = self.partner_id.name[0:120]
            else:
                if self.partner_id.parent_id:
                    nombrerazon = self.partner_id.parent_id.name[0:120]
                else:
                    nombrerazon = self.partner_id.name[0:120]
        else:
            nombrerazon = self.company_id.name[0:120]

        if self.journal_id:
            if self.journal_id.sii_summary_invoice:
                if not self.sii_first_invoice:
                    raise UserError(_('You have to select one first invoice in SII Tab.'))

        if self.move_type in ['out_invoice', 'out_refund']:
            tipo_desglose = self._get_sii_out_taxes(sii_map)
            if self.move_type == 'out_refund' and self.sii_rectificative_type == 'I':
                    importe_total = -abs(self.amount_total)
            else:
                importe_total = self.amount_total
            if (self.currency_id != self.company_id.currency_id):
                importe_total = round(self.currency_id.with_context(date=self._get_currency_rate_date()).compute(importe_total, self.company_id.currency_id), 2)

            vat = self._get_vat_number(company.vat)
            invoices = {
                "IDFactura": {
                    "IDEmisorFactura": {
                        "NIF": vat
                    },
                    "NumSerieFacturaEmisor": self.name[0:60],
                    "FechaExpedicionFacturaEmisor": invoice_date},
                "FacturaExpedida": {
                    "TipoFactura": invoice_type,
                    "ClaveRegimenEspecialOTrascendencia": key,
                    "DescripcionOperacion": self.sii_description[0:500],
                    "Contraparte": {
                        "NombreRazon": nombrerazon
                    },
                    "TipoDesglose": tipo_desglose,
                    "ImporteTotal": round(importe_total, 2)
                }
            }
            if self.partner_id.anonymous_customer and self.move_type in ['out_invoice', 'out_refund']:
                del invoices['FacturaExpedida']['Contraparte']

            #Si tiene factura vinculada
            if self.reversed_entry_id:
                invoices['FacturaExpedida']['FacturasRectificadas'] = {
                    'IDFacturaRectificada': {
                        'NumSerieFacturaEmisor': self.reversed_entry_id.name,
                        'FechaExpedicionFacturaEmisor': self._change_date_format(self.reversed_entry_id.invoice_date)
                    }
                }

            if self.journal_id:
                if self.journal_id.sii_summary_invoice:
                    del invoices['FacturaExpedida']['Contraparte']
                    invoices['IDFactura']["NumSerieFacturaEmisor"] = self.sii_first_invoice and self.sii_first_invoice.name[0:60]
                    invoices['IDFactura']["NumSerieFacturaEmisorResumenFin"] = self.name[0:60]
            if sii_map.version == '1.0':
                invoices['PeriodoImpositivo'] = {
                    "Ejercicio": ejercicio,
                    "Periodo": periodo
                }
            else:
                invoices['PeriodoLiquidacion'] = {
                    "Ejercicio": ejercicio,
                    "Periodo": periodo
                }
                if self.amount_total >= 100000000:
                    invoices['FacturaExpedida']['Macrodato'] = 'S'
            # Uso condicional de IDOtro/NIF
            if (self.journal_id and not self.journal_id.sii_summary_invoice) and not self.partner_id.anonymous_customer:
                invoices['FacturaExpedida']['Contraparte'].update(self._get_sii_identifier())
            if self.move_type == 'out_refund':
                invoices['FacturaExpedida']['TipoRectificativa'] = self.sii_rectificative_type

                if self.sii_rectificative_type == 'S':
                    base_rectificada = 0
                    cuota_rectificada = 0
                    base_rectificada += self.reversed_entry_id.amount_untaxed
                    cuota_rectificada += self.reversed_entry_id.amount_tax
                    invoices['FacturaExpedida']['ImporteRectificacion'] = {
                        'BaseRectificada': base_rectificada,
                        'CuotaRectificada': cuota_rectificada
                    }

            if not self.partner_id.anonymous_customer:
                vat = ''.join(e for e in self.partner_id.vat if e.isalnum()).upper()
                code = self._get_country_code(vat)
                if self.journal_id and not self.journal_id.sii_summary_invoice:
                    if ('IDOtro' in invoices['FacturaExpedida']['Contraparte'] or
                        ('NIF' in invoices['FacturaExpedida']['Contraparte'] and
                         invoices['FacturaExpedida']['Contraparte']['NIF'].startswith(
                            'N') and code == 'ES')):
                        if 'DesgloseFactura' in invoices[
                                'FacturaExpedida']['TipoDesglose']:
                            if 'DesgloseTipoOperacion' not in invoices[
                                    'FacturaExpedida']['TipoDesglose']:
                                invoices['FacturaExpedida']['TipoDesglose'][
                                    'DesgloseTipoOperacion'] = {}
                            invoices['FacturaExpedida']['TipoDesglose'][
                                'DesgloseTipoOperacion']['Entrega'] = invoices[
                                    'FacturaExpedida']['TipoDesglose'][
                                        'DesgloseFactura']
                            invoices['FacturaExpedida']['TipoDesglose'].pop(
                                'DesgloseFactura')

        if self.move_type in ['in_invoice', 'in_refund']:
            desglose_factura = self._get_sii_in_taxes(sii_map)
            cuota_deducible = 0
            if 'DesgloseIVA' in desglose_factura:
                for desglose in desglose_factura['DesgloseIVA']['DetalleIVA']:
                    cuota_deducible += desglose['CuotaSoportada']

            if 'InversionSujetoPasivo' in desglose_factura:
                for desglose in desglose_factura['InversionSujetoPasivo']['DetalleIVA']:
                    cuota_deducible += desglose['CuotaSoportada']
            
            nodeducible_taxes = sii_map._get_group_taxes('in', ['SFRND'])
            if nodeducible_taxes:
                for tax_line in self.line_ids:
                    if tax_line.tax_line_id and tax_line.tax_line_id.id in nodeducible_taxes.ids:
                        cuota_deducible = cuota_deducible - tax_line.balance

            # "Cuota Deducible" is 0 when RE are in lines
            re_taxes = sii_map._get_group_taxes('in', ['SRE'])
            if re_taxes:
                for tax_line in self.line_ids:
                    if tax_line.tax_line_id and tax_line.tax_line_id.id in re_taxes.ids:
                        cuota_deducible = 0

            reg_date = self._change_date_format(self.date or fields.Date.today())
            if self.move_type == 'in_refund' and self.sii_rectificative_type == 'I':
                    importe_total = -abs(self.amount_total)
            else:
                importe_total = self.amount_total
            if (self.currency_id != self.company_id.currency_id):
                importe_total = round(self.currency_id.with_context(date=self._get_currency_rate_date()).compute(importe_total, self.company_id.currency_id), 2)
            
            taxes_irpf = sii_map._get_group_taxes('in', ['SFRR'])
            if taxes_irpf:
                importe_total = importe_total - sum([p.balance for p in self.line_ids.filtered(lambda x: x.tax_line_id and x.tax_line_id.id in taxes_irpf.ids)])

            if not self.ref:
                raise UserError(_('The invoice supplier number is required'))
            invoices = {
                "IDFactura": {
                    "IDEmisorFactura": {},
                    "NumSerieFacturaEmisor":
                    self.ref and
                    self.ref[0:60],
                    "FechaExpedicionFacturaEmisor": invoice_date},
                "FacturaRecibida": {
                    "TipoFactura": invoice_type,
                    "ClaveRegimenEspecialOTrascendencia": key,
                    "DescripcionOperacion": self.sii_description[0:500],
                    "DesgloseFactura": desglose_factura,
                    "Contraparte": {
                        "NombreRazon": nombrerazon
                    },
                    "FechaRegContable": reg_date,
                    "CuotaDeducible": round(cuota_deducible, 2),
                    "ImporteTotal": round(importe_total, 2)
                }
            }

            #Si tiene factura vinculada
            if self.reversed_entry_id:
                invoices['FacturaRecibida']['FacturasRectificadas'] = {
                    'IDFacturaRectificada': {
                        'NumSerieFacturaEmisor': self.reversed_entry_id.ref,
                        'FechaExpedicionFacturaEmisor': self._change_date_format(self.reversed_entry_id.invoice_date)
                    }
                }

            if self.journal_id:
                if self.journal_id.sii_summary_invoice:
                    del invoices['IDFactura']["NumSerieFacturaEmisor"]
                    invoices['IDFactura']["NumSerieFacturaEmisor"] = self.sii_first_invoice and self.sii_first_invoice.name[0:60]
                    invoices['IDFactura']["NumSerieFacturaEmisorResumenFin"] = self.ref and self.ref[0:60]
            if sii_map.version == '1.0':
                invoices['PeriodoImpositivo'] = {
                    "Ejercicio": ejercicio,
                    "Periodo": periodo
                }
            else:
                invoices['PeriodoLiquidacion'] = {
                    "Ejercicio": ejercicio,
                    "Periodo": periodo
                }
                if self.amount_total >= 100000000:
                    invoices['FacturaExpedida']['Macrodato'] = 'S'
            id_emisor = self._get_sii_identifier()

            if self.is_dua:
                invoices["FacturaRecibida"].pop("ImporteTotal", False)
                cvat = ''.join(e for e in self.company_id.vat if e.isalnum()).upper()
                cnif = self._get_vat_number(cvat)
                id_emisor = {'NIF': cnif}

            invoices['IDFactura']['IDEmisorFactura'].update(id_emisor)
            if self.journal_id and not self.journal_id.sii_summary_invoice:
                invoices['FacturaRecibida']['Contraparte'].update(id_emisor)
            if self.move_type == 'in_refund':
                invoices['FacturaRecibida']['TipoRectificativa'] = self.sii_rectificative_type

                if self.sii_rectificative_type == 'S':
                    base_rectificada = 0
                    cuota_rectificada = 0
                    for s in self.refund_invoice_ids:
                        base_rectificada += s.amount_untaxed
                        cuota_rectificada += s.amount_tax
                    invoices['FacturaRecibida']['ImporteRectificacion'] = {
                        'BaseRectificada': base_rectificada,
                        'CuotaRectificada': cuota_rectificada
                    }
        return invoices

    def _send_invoice_to_sii(self):
        result_job_object = self.env['sii.result'].sudo()
        for invoice in self.filtered(lambda i: i.state in ['posted'] and i.is_sii_available and i.sii_state in ['not_sent', 'error', 'sent_modified', 'cancelled_modified']):
            sii_map = self.env['sii.map']._get_current_map()
            sii_agency_id = invoice.company_id.sii_agency_id
            if invoice.move_type in ['out_invoice', 'out_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_out')
                port_name = 'SuministroFactEmitidas'
                operation = 'SuministroLRFacturasEmitidas'
            elif self.move_type in ['in_invoice', 'in_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_in')
                port_name = 'SuministroFactRecibidas'
                operation = 'SuministroLRFacturasRecibidas'
            type_communication = 'A0'
            if invoice.sii_csv:
                # If sii_csv is filled means that already in SII so, all next request are for modify.
                type_communication = 'A1'
            header = invoice._get_header(type_communication, sii_map)
            invoices = invoice._get_invoices(sii_map)
            try:
                res = invoice._send_soap(wsdl, port_name, operation, header, invoices)
                # TODO Facturas intracomunitarias 66 RIVA
                # elif invoice.fiscal_position.id == self.env.ref(
                #     'account.fp_intra').id:
                #     res = serv.SuministroLRDetOperacionIntracomunitaria(
                #         header, invoices)

                vals = {}
                if res['EstadoEnvio'] in ['Correcto', 'ParcialmenteCorrecto']:
                    if res['EstadoEnvio'] in ['Correcto']:
                        vals.update({'sii_state': 'sent'})
                    if res['EstadoEnvio'] in ['ParcialmenteCorrecto']:
                        vals.update({'sii_state': 'accepted_with_errors'})
                    vals.update({
                        'sii_error_message': False,
                        'sii_csv': res['CSV'],
                    })
                else:
                    vals.update({
                        'sii_state': 'error',
                    })
                    invoice.sudo()._create_fail_activity()
                result_job_object.registry_result(invoice, res, 'normal', False, 'account.move')
                res_line = res['RespuestaLinea'][0]
                if res_line['CodigoErrorRegistro']:
                    send_error = "{} | {}".format(str(res_line['CodigoErrorRegistro']), str(res_line['DescripcionErrorRegistro']))
                    vals.update({
                        'sii_error_message': send_error,
                    })
                
                invoice.write(vals)

            except Exception as fault:
                vals = {}
                result_job_object.registry_result(invoice, False, 'normal', fault, 'account.move')
                vals.update({
                    'sii_state': 'error',
                    'sii_error_message': str(fault)
                })
                invoice.write(vals)
                invoice.sudo()._create_fail_activity()

            if invoice.sii_state in ['sent', 'accepted_with_errors',]:
                invoice.sudo().activity_ids.filtered(lambda x: x.summary == 'SII Error: ' + invoice.name)._action_done()

    def send_sii(self):
        queue_obj = self.env['queue.job'].sudo()
        for invoice in self:
            company = invoice.company_id
            if company.is_sii_active and invoice.is_sii_available:
                if not company.use_queue:
                    invoice._send_invoice_to_sii()
                else:
                    eta = company._get_time()
                    new_delay = self.sudo().with_context(
                        company_id=company.id
                    ).with_delay(eta=eta).confirm_one_invoice(invoice)
                    job = queue_obj.search([
                        ('uuid', '=', new_delay.uuid)
                    ], limit=1)
                    invoice.sudo().move_jobs_ids |= job

    def action_post(self):
        res = super(AccountMove, self).action_post()
        queue_obj = self.env['queue.job'].sudo()
        for invoice in self:
            company = invoice.company_id
            if company.is_sii_active and company.sii_send_moves_on == 'validate' and invoice.is_sii_available:
                if not company.use_queue:
                    invoice._send_invoice_to_sii()
                else:
                    eta = company._get_time()
                    new_delay = self.sudo().with_context(company_id=company.id).with_delay(eta=eta).confirm_one_invoice(invoice)
                    job = queue_obj.search([('uuid', '=', new_delay.uuid)], limit=1)
                    invoice.sudo().move_jobs_ids |= job
        return res

    def button_cancel(self):
        for queue in self.move_jobs_ids:
            if queue.state == 'started':
                raise UserError(_('You can not cancel this invoice because there is a job running!'))
            elif queue.state in ('pending', 'enqueued', 'failed'):
                queue.write({
                    'state': 'done',
                    'date_done': date.today()
                })
        return super(AccountMove, self).button_cancel()

    def send_recc_payment_registry(self):
        for invoice in self.filtered(lambda x: x.sii_state in ['sent', 'accepted_with_errors', 'sent_modified']):
            sii_map = self.env['sii.map']._get_current_map()
            sii_agency_id = invoice.company_id.sii_agency_id
            if invoice.move_type in ['out_invoice', 'out_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_pr')
                port_name = 'SuministroCobrosEmitidas'
                operation = 'SuministroLRCobrosEmitidas'
            elif invoice.move_type in ['in_invoice', 'in_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_ps')
                port_name = 'SuministroPagosRecibidas'
                operation = 'SuministroLRPagosRecibidas'
            header = invoice._get_header(False, sii_map)

            payments = invoice.invoice_payments_widget.get("content")

            for payment in payments:
                if payment.get('account_payment_id', False):
                    payment_obj = self.env['account.payment'].browse([payment.get('account_payment_id')])

                    if not payment_obj.sii_state or payment_obj.sii_state != 'sent':

                        fecha = self._change_date_format(payment_obj.date)
                        medio = payment_obj.method_used
                        importe = round(payment_obj.amount, 2)
                        cuenta_o_medio = payment_obj.partner_bank_id and payment_obj.partner_bank_id.acc_number or False

                        pay = {
                            'Fecha': fecha,
                            'Importe': importe,
                            'Medio': medio
                        }

                        if cuenta_o_medio:
                            pay.update({
                                'Cuenta_O_Medio': cuenta_o_medio
                            })

                        try:
                            invoice_date = self._change_date_format(invoice.invoice_date)
                            if invoice.move_type in ['out_invoice', 'out_refund']:
                                nif = self._get_vat_number(invoice.company_id.vat)
                                payment = {
                                    "IDFactura": {
                                        "IDEmisorFactura": {
                                            "NIF": nif
                                        },
                                        "NumSerieFacturaEmisor": invoice.name[0:60],
                                        "FechaExpedicionFacturaEmisor": invoice_date},
                                }
                                payment['Cobros'] = {}
                                payment['Cobros']['Cobro'] = []
                                payment['Cobros']['Cobro'].append(pay)
                            elif invoice.move_type in ['in_invoice', 'in_refund']:
                                payment = {
                                    "IDFactura": {
                                        "IDEmisorFactura": {
                                            "NombreRazon": invoice.partner_id.name[0:120]
                                        },
                                        "NumSerieFacturaEmisor":
                                        invoice.ref and
                                        invoice.ref[0:60],
                                        "FechaExpedicionFacturaEmisor": invoice_date},
                                }
                                id_emisor = invoice._get_sii_identifier()
                                payment['IDFactura']['IDEmisorFactura'].update(id_emisor)
                                payment['Pagos'] = {}
                                payment['Pagos']['Pago'] = []
                                payment['Pagos']['Pago'].append(pay)
                            res = invoice._send_soap(
                                wsdl, port_name, operation, header, payment)
                            if res['EstadoEnvio'] in ['Correcto', 'AceptadoConErrores']:
                                invoice.sii_recc_sent = True
                                payment_obj.sii_state = 'sent'
                                invoice.sii_recc_csv = res['CSV']
                            else:
                                invoice.sii_recc_sent = False
                            self.env['sii.result'].sudo().registry_result(invoice, res, 'recc', False, 'account.move')
                            send_recc_error = False
                            res_line = res['RespuestaLinea'][0]
                            if res_line['CodigoErrorRegistro']:
                                send_recc_error = "{} | {}".format(
                                    str(res_line['CodigoErrorRegistro']),
                                    str(res_line['DescripcionErrorRegistro'])[:60])
                            invoice.sii_recc_send_error = send_recc_error
                        except Exception as fault:
                            self.env['sii.result'].sudo().registry_result(invoice, False, 'recc', fault, 'account.move')
                            invoice.sii_recc_send_error = fault

    def send_recc_payment(self):
        queue_obj = self.env['queue.job'].sudo()
        for invoice in self:
            company = invoice.company_id
            if company.is_sii_active and invoice.is_sii_available:
                if not company.use_queue:
                    invoice.send_recc_payment_registry()
                else:
                    eta = company._get_time()
                    new_delay = self.sudo().with_context(company_id=company.id).with_delay(eta=eta).send_recc_payment_job(invoice)
                    job = queue_obj.search([('uuid', '=', new_delay.uuid)], limit=1)
                    invoice.sudo().move_jobs_ids |= job

    def drop_sii(self):
        queue_obj = self.env['queue.job'].sudo()
        for invoice in self:
            company = invoice.company_id
            if company.is_sii_active:
                if not company.use_queue:
                    invoice._drop_invoice()
                else:
                    eta = company._get_time()
                    new_delay = self.sudo().with_context(company_id=company.id).with_delay(eta=eta).drop_one_invoice(invoice)
                    job = queue_obj.search([('uuid', '=', new_delay.uuid)], limit=1)
                    invoice.sudo().move_jobs_ids |= job

    def _drop_invoice(self):
        queue_obj = self.env['queue.job'].sudo()
        result_job_object = self.env['sii.result'].sudo()
        for invoice in self.filtered(lambda i: i.state in ['cancel']):
            sii_map = self.env['sii.map']._get_current_map()
            company = invoice.company_id
            sii_agency_id = company.sii_agency_id
            nif = self._get_vat_number(company.vat)
            if invoice.move_type in ['out_invoice', 'out_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_out')
                port_name = 'SuministroFactEmitidas'
                operation = 'AnulacionLRFacturasEmitidas'
                number = invoice.name[0:60]
                id_emisor = {"NIF": nif}
            elif self.move_type in ['in_invoice', 'in_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_in')
                port_name = 'SuministroFactRecibidas'
                operation = 'AnulacionLRFacturasRecibidas'
                number = invoice.ref and invoice.ref[0:60]
                id_emisor = self._get_sii_identifier()
                id_emisor['NombreRazon'] = self.partner_id.name
            header = invoice._get_header(False, sii_map)
            ejercicio = fields.Date.from_string(self.date).year
            periodo = '%02d' % fields.Date.from_string(self.date).month
            invoice_date = self._change_date_format(invoice.invoice_date)
            try:
                query = {
                    "PeriodoLiquidacion": {
                        "Ejercicio": ejercicio,
                        "Periodo": periodo
                    },
                    "IDFactura": {
                        "IDEmisorFactura": id_emisor,
                        "NumSerieFacturaEmisor": number,
                        "FechaExpedicionFacturaEmisor": invoice_date
                    }
                }
                res = invoice._send_soap(wsdl, port_name, operation, header, query)
                vals = {}
                if res['EstadoEnvio'] in ['Correcto', 'ParcialmenteCorrecto']:
                    vals.update({
                        'sii_state': 'cancelled',
                        'sii_error_message': False,
                        'sii_csv': res['CSV']
                    })
                else:
                    vals.update({
                        'sii_state': 'error',
                    })

                result_job_object.registry_result(invoice, res, 'normal', False, 'account.move')
                res_line = res['RespuestaLinea'][0]
                if res_line['CodigoErrorRegistro']:
                    send_error = "{} | {}".format(str(res_line['CodigoErrorRegistro']), str(res_line['DescripcionErrorRegistro']))
                    vals.update({
                        'sii_error_message': send_error,
                    })

                    if res_line['CodigoErrorRegistro'] == 3001:
                        # Means that is already cancelled so there is no error
                        vals.update({
                            'sii_state': 'cancelled'
                        })

                invoice.write(vals)
            except Exception as fault:
                self.env['sii.result'].sudo().registry_result(invoice, False, 'normal', fault, 'account.move')

    def check_sii(self):
        queue_obj = self.env['queue.job'].sudo()
        for invoice in self:
            company = invoice.company_id
            if company.is_sii_active:
                if not company.use_queue:
                    invoice._check_invoice()
                else:
                    eta = company._get_time()
                    new_delay = self.sudo().with_context(company_id=company.id).with_delay(eta=eta).check_one_invoice(invoice)
                    job = queue_obj.search([('uuid', '=', new_delay.uuid)], limit=1)
                    invoice.sudo().move_jobs_ids |= job

    def _check_invoice(self):
        for invoice in self.filtered(lambda i: i.state in ['posted']):
            sii_map = self.env['sii.map']._get_current_map()
            sii_agency_id = invoice.company_id.sii_agency_id
            if invoice.move_type in ['out_invoice', 'out_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_out')
                port_name = 'SuministroFactEmitidas'
                operation = 'ConsultaLRFacturasEmitidas'
                number = invoice.name[0:60]
            elif self.move_type in ['in_invoice', 'in_refund']:
                wsdl = sii_agency_id._get_wsdl('wsdl_in')
                port_name = 'SuministroFactRecibidas'
                operation = 'ConsultaLRFacturasRecibidas'
                number = invoice.ref and invoice.ref[0:60]
            header = invoice._get_header(False, sii_map)
            ejercicio = fields.Date.from_string(self.date).year
            periodo = '%02d' % fields.Date.from_string(self.date).month
            invoice_date = self._change_date_format(invoice.invoice_date)
            try:
                query = {
                    "IDFactura": {
                        "NumSerieFacturaEmisor": number,
                        "FechaExpedicionFacturaEmisor": invoice_date
                    }
                }
                if sii_map.version == '1.0':
                    query['PeriodoImpositivo'] = {
                        "Ejercicio": ejercicio,
                        "Periodo": periodo
                    }
                else:
                    query['PeriodoLiquidacion'] = {
                        "Ejercicio": ejercicio,
                        "Periodo": periodo
                    }
                res = invoice._send_soap(wsdl, port_name, operation, header, query)
                self.env['sii.check.result'].sudo().registry_result(invoice, res, False, 'account.move')
            except Exception as fault:
                self.env['sii.check.result'].sudo().registry_result(invoice, False, fault, 'account.move')

    def check_one_invoice(self, invoice):
        invoice._check_invoice()

    def confirm_one_invoice(self, invoice):
        invoice._send_invoice_to_sii()

    def drop_one_invoice(self, invoice):
        invoice._drop_invoice()

    def send_recc_payment_job(self, invoice):
        invoice.send_recc_payment_registry()

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self,):
        res = super(AccountMoveLine, self).reconcile()

        moves = self.mapped('move_id')
        for move in moves:
            if move.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                if move.sii_reg_key_id and move.sii_reg_key_id.code == '07':
                    move.send_recc_payment()

        return res
