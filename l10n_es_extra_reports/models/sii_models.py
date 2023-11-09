# -*- coding: utf-8 -*-

import re

from datetime import datetime

from odoo import fields, models, api, _, exceptions
from odoo.osv import expression
from odoo.addons import decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

TYPE = [
    ('normal', 'Normal'),
    ('recc', 'RECC')
]

RESULTS = [
    ('ConDatos', 'With data'),
    ('SinDatos', 'Without data')
]

RECONCILE = [
    ('1', _('Not verifiable')),
    ('2', _('In contrast process')),
    ('3', _('Not contrasted')),
    ('4', _('Partially contrasted')),
    ('5', _('Contrasted'))
]

class Agency(models.Model):
    _name = 'sii.agency'
    _description = _("Agency")

    name = fields.Char(string=_("Name"), required=True)

    date_from = fields.Date(string=_('Date from'))
    date_to = fields.Date(string=_('Date to'))
    version = fields.Char(string=_('Version'))
    wsdl_url = fields.One2many('sii.wsdl', 'sii_agency_id', string=_("WSDL URL"))

    def _get_wsdl(self, key):
        self.ensure_one()
        sii_wsdl = self.wsdl_url.search([('sii_agency_id', '=', self.id), ('key', '=', key)], limit=1)
        if sii_wsdl:
            wsdl = sii_wsdl.wsdl
        else:
            raise exceptions.Warning(_('WSDL not found. Check your configuration'))
        return wsdl

class Wsdl(models.Model):
    _name = 'sii.wsdl'
    _description = _('WDSL Urls')
    
    name = fields.Char(string=_('Name'))
    key = fields.Char(string=_('Key'), readonly=True)
    wsdl = fields.Char(string=_('WDSL Url'))
    sii_agency_id = fields.Many2one('sii.agency', string=_('Agency'), ondelete='cascade')

class Certificate(models.Model):
    _name = 'sii.certificate'
    _description = _("SII Certificate")

    def _get_default_folder_name(self):
        return "/var/lib/odoo/filestore/%s/certificates" % self.env.cr.dbname or 'name_of_database'

    name = fields.Char(string=_("Name"), help=_("Name of certificate. Filled from certificate"))
    state = fields.Selection([('draft', _('Draft')), ('decrypted', _('Decrypted')), ('active', _('Active'))], string=_("State"), default="draft")
    file = fields.Binary(string=_("File"), required=True)
    folder = fields.Char(string=_("Folder Name"), required=True, default=_get_default_folder_name, help=_("Route to the folder where to save the certificate."))
    date_start = fields.Date(string=_("Start Date"), help=_("Start date for certificate. Filled from certificate."))
    date_end = fields.Date(string=_("End Date"), help=_("End date for certificate. Filled from certificate."))
    public_key = fields.Char(string=_("Public Key"), readonly=True)
    private_key = fields.Char(string=_("Private Key"), readonly=True)
    company_id = fields.Many2one("res.company", string=_("Company"), required=True, default=lambda self: self.env.user.company_id.id)

    def write(self, vals):
        result = super(Certificate, self).write(vals)
        for record in self:
            if record.state == 'active':
                if record.public_key:
                    self.env['ir.config_parameter'].sudo().set_param("l10n_es_extra_reports.public_key", record.public_key)
                if record.private_key:
                    self.env['ir.config_parameter'].sudo().set_param("l10n_es_extra_reports.private_key", record.private_key)

        return result

    def action_password_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Insert Certificate Password'),
            'res_model': 'sii.certificate.password',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_active(self):
        if self.state != 'decrypted' or not self.public_key or not self.private_key:
            raise exceptions.UserError(_("You can't activate this certificate. Please generate the public and private key through 'Obtain keys' button then activate again."))

        other_configs = self.search([('id', '!=', self.id), ('company_id', '=', self.company_id.id)])
        for config_id in other_configs:
            config_id.state = 'draft'
        self.state = 'active'

class CauseExemption(models.Model):
    _name = 'sii.cause.exemption'
    _description = _('Cause Exemption')

    code = fields.Char(string=_('Code'), required=True)
    name = fields.Char(string=_('Name'), required=True)

    def name_get(self):
        vals = []
        for record in self:
            name = '[{}] - {}'.format(record.code, record.name)
            vals.append(tuple([record.id, name]))
        return vals

class InvoiceType(models.Model):
    _name = 'sii.invoice.type'
    _description = _('Invoice Type')

    code = fields.Char(string=_('Code'), required=True)
    name = fields.Char(string=_('Name'), required=True)
    type = fields.Selection(selection=[('invoice', _('Invoice')), ('refund', _('Refund')), ('other', _('Other'))], string=_('Type'), required=True)
    default = fields.Boolean(string=_('Default'))

    def name_get(self):
        vals = []
        for record in self:
            name = '[{}] - {}'.format(record.code, record.name)
            vals.append(tuple([record.id, name]))
        return vals

class OperationType(models.Model):
    _name = 'sii.operation.type'
    _description = _('Operation Type')

    code = fields.Char(string=_('Code'), required=True)
    name = fields.Char(string=_('Name'), required=True)

    def name_get(self):
        vals = []
        for record in self:
            name = '[{}] - {}'.format(record.code, record.name)
            vals.append(tuple([record.id, name]))
        return vals

class PropertySituation(models.Model):
    _name = 'sii.property.situation'
    _description = _('Property Situation')

    code = fields.Char(string=_('Code'), required=True)
    name = fields.Char(string=_('Name'), required=True)

    def name_get(self):
        vals = []
        for record in self:
            name = '[{}] - {}'.format(record.code, record.name)
            vals.append(tuple([record.id, name]))
        return vals

class RegKey(models.Model):
    _name = 'sii.reg.key'
    _description = _('Registration Key')

    code = fields.Char(string=_('Code'), required=True, size=2)
    name = fields.Char(string=_('Name'), required=True)
    type = fields.Selection(selection=[('sale', _('Sale')), ('purchase', _('Purchase'))], string=_('Type'), required=True)

    def name_get(self):
        vals = []
        for record in self:
            name = '[{}] - {}'.format(record.code, record.name)
            vals.append(tuple([record.id, name]))
        return vals

class Map(models.Model):
    _name = 'sii.map'
    _description = _('Map')

    @api.constrains('date_from', 'date_to')
    def _unique_date(self):
        domain = [('id', '!=', self.id)]
        if self.date_from and self.date_to:
            domain += [
                '|',
                   ('date_from', '<=', self.date_to),
                   ('date_from', '>=', self.date_from),
                '|',
                   ('date_to', '<=', self.date_to),
                   ('date_to', '>=', self.date_from),
                '|',
                   ('date_from', '=', False),
                   ('date_to', '>=', self.date_from),
                '|',
                   ('date_to', '=', False),
                   ('date_from', '<=', self.date_to),
            ]
        elif self.date_from:
            domain += [('date_to', '>=', self.date_from)]
        elif self.date_to:
            domain += [('date_from', '<=', self.date_to)]
        dates = self.search(domain)
        if dates:
            raise exceptions.Warning(_("Error! Dates already existing in other record."))

    name = fields.Char(string=_("Name"), required=True)

    #Comun fields on map
    out_map_line_ids = fields.One2many('sii.map.line', 'out_map_id', string=_('Out invoice map'))
    in_map_line_ids = fields.One2many('sii.map.line', 'in_map_id', string=_('In invoice map'))

    #Fields used on map sii
    date_from = fields.Date(string=_('Date from'))
    date_to = fields.Date(string=_('Date to'))
    version = fields.Char(string=_('Version'))

    def _get_current_map(self):
        now = datetime.now().date()
        return self.search(['&', '|', ('date_from', '=', False), ('date_from', '<=', now), '|', ('date_to', '=', False), ('date_to', '>=', now)], limit=1)

    def _get_map_tax_template(self, template, company_ids=False):
        tax_obj = self.env['account.tax']
        if not template:
            return tax_obj

        criteria = ['|', ('name', '=', template.name), ('description', '=', template.name)]
        if template.description:
            criteria = expression.OR([criteria, ['|', ('description', '=', template.description), ('name', '=', template.description)]])
        if company_ids:
            criteria = expression.AND([criteria, [('company_id', 'in', company_ids)]])

        taxes = tax_obj.search(criteria)

        # We havent found any taxes by name or description, maybe they have changed the name.
        # Try searching by external
        if not taxes:
            model_data = self.env['ir.model.data'].sudo().search([('model', '=', 'account.tax.template'), ('res_id', '=', template.id)], limit=1)
            if model_data:
                domain = [('model', '=', 'account.tax')]
                if company_ids:
                    company_domain = []
                    for company_id in company_ids:
                        company_domain = expression.OR([company_domain, [('name', 'ilike', str(company_id) + "_" + str(model_data.name))]])
                    if company_domain:
                        domain = expression.AND([domain, company_domain])
                else:
                    domain.append(('name', 'ilike', str(model_data.name)))

                possible_taxes = self.env['ir.model.data'].sudo().search(domain)
                if possible_taxes:
                    possible_names = [p.name for p in possible_taxes]
                    pattern = re.compile(".*_"+model_data.name+"$")
                    correct_names = list(filter(pattern.match, possible_names))
                    if correct_names:
                        for possible in possible_taxes:
                            if possible.name in correct_names:
                                taxes = tax_obj.browse(possible.res_id)

        return taxes

    def _get_map_line_id(self, type, tax):
        founded_map_line = self.env['sii.map.line']
        if type == 'out':
            for map_line in self.out_map_line_ids:
                for template in map_line.taxes:
                    taxes = self._get_map_tax_template(template)
                    if tax in taxes:
                        founded_map_line = map_line
                    if founded_map_line:
                        continue
                if founded_map_line:
                    continue
        if type == 'in':
            for map_line in self.in_map_line_ids:
                for template in map_line.taxes:
                    taxes = self._get_map_tax_template(template)
                    if tax in taxes:
                        founded_map_line = map_line
                    if founded_map_line:
                        continue
                if founded_map_line:
                    continue
        return founded_map_line

    def _get_group(self, type, code):
        tax_ids = self.env['account.tax']
        exemption_ids = self.env['sii.cause.exemption']
        operation_type_ids = self.env['sii.operation.type']
        for r in self:
            if type == 'out':
                for map_line in r.out_map_line_ids.filtered(lambda x: x.code == code):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)
                    if map_line.operation_type_id:
                        operation_type_ids |= map_line.operation_type_id
                    if map_line.cause_exemption_id:
                        exemption_ids |= map_line.cause_exemption_id
            elif type == 'in':
                for map_line in r.in_map_line_ids.filtered(lambda x: x.code == code):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)
                    if map_line.operation_type_id:
                        operation_type_ids |= map_line.operation_type_id
                    if map_line.cause_exemption_id:
                        exemption_ids |= map_line.cause_exemption_id

        return tax_ids, operation_type_ids, exemption_ids

    def _get_group_taxes(self, type, codes):
        tax_ids = self.env['account.tax']
        for r in self:
            if type == 'out':
                for map_line in r.out_map_line_ids.filtered(lambda x: x.code in codes):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)
            elif type == 'in':
                for map_line in r.in_map_line_ids.filtered(lambda x: x.code in codes):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)

        return tax_ids        

    def _get_all_taxes(self, type, exclude=[]):
        tax_ids = self.env['account.tax']
        for r in self:
            if type == 'out':
                for map_line in r.out_map_line_ids.filtered(lambda x: x.code not in exclude):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)
            elif type == 'in':
                for map_line in r.in_map_line_ids.filtered(lambda x: x.code not in exclude):
                    for template in map_line.taxes:
                        tax_ids |= r._get_map_tax_template(template)
        return tax_ids

class MapLine(models.Model):
    _name = 'sii.map.line'
    _description = _('Map Line')

    code = fields.Char(string=_('Code'), required=True)
    operation_type_id = fields.Many2one('sii.operation.type', string=_('Operation Type'))
    cause_exemption_id = fields.Many2one('sii.cause.exemption', string=_('Cause Exemption'))
    name = fields.Char(string=_('Name'))
    taxes = fields.Many2many('account.tax.template', string=_("Taxes"))
    out_map_id = fields.Many2one('sii.map', string=_('Out Invoice Map'))
    in_map_id = fields.Many2one('sii.map', string=_('In Invoice Map'))

class Result(models.Model):
    _name = 'sii.result'
    _description = _('SII Result')
    _order = 'id desc'
    _rec_name = 'sii_name'

    sii_csv = fields.Char(string=_('CSV'))
    sii_presented_vat = fields.Char(string=_('Presented VAT'))
    sii_presented_datetime = fields.Datetime(string=_('Presented Datetime'))
    sii_version = fields.Char(string=_('Version of SII'))
    sii_name = fields.Char(string=_('Company Name'))
    sii_represented_vat = fields.Char(string=_('Represented VAT'))
    sii_vat = fields.Char(string=_('Vat'))
    sii_communication_type = fields.Char(string=_('Communication Type'))
    sii_sent_state = fields.Char(string=_('Sent State'))
    sii_sender_vat = fields.Char(string=_('Sender VAT'))
    sii_sender_type_id = fields.Char(string=_('Type ID'))
    sii_sender_number_id = fields.Char(string=_('Number ID'))
    sii_sender_country_code = fields.Char(string=_('Country Code'))
    sii_invoice_number = fields.Char(string=_('Invoice number'))
    sii_invoice_number_resume = fields.Char(string=_('Invoice number end resume'))
    sii_invoice_date = fields.Date(string=_('Date Invoice'))
    sii_registry_state = fields.Char(string=_('Registry State'))
    sii_registry_error_code = fields.Char(string=_('Registry Error Code'))
    sii_registry_error_description = fields.Char(string=_('Registry Error Description'))
    sii_registry_csv = fields.Char(string=_('Registry CSV'))
    sii_type = fields.Selection(TYPE, _('Type'))
    sii_move_id = fields.Many2one('account.move', string=_('Move'))
    sii_duplicate_registry_state = fields.Char(string=_('State'))
    sii_duplicate_registry_error_code = fields.Char(string=_('Error code'))
    sii_duplicate_registry_error_des = fields.Char(string=_('Error description'))

    def registry_result(self, record, res, type, fault, model):
        vals = {
            'sii_type': type,
        }
        if model == 'account.move':
            vals['sii_move_id'] = record.id
        if fault:
            vals['sii_registry_error_description'] = fault
        else:
            if 'CSV' in res:
                vals['sii_csv'] = res['CSV']
            if 'DatosPresentacion' in res and res['DatosPresentacion']:
                if 'NIFPresentador' in res['DatosPresentacion']:
                    vals['sii_presented_vat'] = res['DatosPresentacion']['NIFPresentador']
                if 'TimestampPresentacion' in res['DatosPresentacion']:
                    date = datetime.strptime(res['DatosPresentacion']['TimestampPresentacion'], '%d-%m-%Y %H:%M:%S')
                    new_date = datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
                    vals['sii_presented_datetime'] = new_date
            if 'Cabecera' in res:
                if 'IDVersionSii' in res['Cabecera']:
                    vals['sii_version'] = res['Cabecera']['IDVersionSii']
                if 'Titular' in res['Cabecera']:
                    if 'NombreRazon' in res['Cabecera']['Titular']:
                        vals['sii_name'] = res['Cabecera']['Titular']['NombreRazon']
                    if 'NIFRepresentante' in res['Cabecera']['Titular']:
                        vals['sii_represented_vat'] = res['Cabecera']['Titular']['NIFRepresentante']
                    if 'NIF' in res['Cabecera']['Titular']:
                        vals['sii_vat'] = res['Cabecera']['Titular']['NIF']
                if 'TipoComunicacion' in res['Cabecera']:
                    vals['sii_communication_type'] = res['Cabecera']['TipoComunicacion']
            if 'EstadoEnvio' in res:
                vals['sii_sent_state'] = res['EstadoEnvio']
            if 'RespuestaLinea' in res:
                reply = res['RespuestaLinea'][0]
                if 'IDFactura' in reply:
                    if 'IDEmisorFactura' in reply['IDFactura']:
                        if 'NIF' in reply['IDFactura']['IDEmisorFactura']:
                            vals['sii_sender_vat'] = reply['IDFactura']['IDEmisorFactura']['NIF']
                        if 'IDOtro' in reply['IDFactura']['IDEmisorFactura']:
                            if reply['IDFactura']['IDEmisorFactura']['IDOtro']:
                                if 'CodigoPais' in reply['IDFactura']['IDEmisorFactura']['IDOtro']:
                                    vals['sii_sender_country_code'] = reply['IDFactura'][
                                        'IDEmisorFactura']['IDOtro']['CodigoPais']
                                if 'IDType' in reply['IDFactura']['IDEmisorFactura']['IDOtro']:
                                    vals['sii_sender_type_id'] = reply['IDFactura']['IDEmisorFactura']['IDOtro']['IDType']
                                if 'ID' in reply['IDFactura']['IDEmisorFactura']['IDOtro']:
                                    vals['sii_sender_number_id'] = reply['IDFactura']['IDEmisorFactura']['IDOtro']['ID']
                    if 'NumSerieFacturaEmisor' in reply['IDFactura']:
                        vals['sii_invoice_number'] = reply['IDFactura']['NumSerieFacturaEmisor']
                    if 'NumSerieFacturaEmisorResumenFin' in reply['IDFactura']:
                        vals['sii_invoice_number_resume'] = reply['IDFactura']['NumSerieFacturaEmisorResumenFin']
                    if 'FechaExpedicionFacturaEmisor' in reply['IDFactura']:
                        date = datetime.strptime(reply['IDFactura']['FechaExpedicionFacturaEmisor'], '%d-%m-%Y')
                        new_date = datetime.strftime(date, '%Y-%m-%d')
                        vals['sii_invoice_date'] = new_date
                if 'EstadoRegistro' in reply:
                    vals['sii_registry_state'] = reply['EstadoRegistro']
                if 'CodigoErrorRegistro' in reply:
                    vals['sii_registry_error_code'] = reply['CodigoErrorRegistro']
                if 'DescripcionErrorRegistro' in reply:
                    if record.sii_state == 'cancelled':
                        vals['sii_registry_error_description'] = _('SII Invoice Canceled. Create a new invoice')
                    else:
                        vals['sii_registry_error_description'] = reply['DescripcionErrorRegistro']
                if 'CSV' in reply:
                    vals['sii_registry_csv'] = reply['CSV']
                if 'RegistroDuplicado' in reply and reply['RegistroDuplicado']:
                    duplicate = reply['RegistroDuplicado']
                    if 'EstadoRegistro' in duplicate:
                        vals['sii_duplicate_registry_state'] = duplicate['EstadoRegistro']
                    if 'CodigoErrorRegistro' in duplicate:
                        vals['sii_duplicate_registry_error_code'] = duplicate['CodigoErrorRegistro']
                    if 'DescripcionErrorRegistro' in duplicate:
                        vals['sii_duplicate_registry_error_des'] = duplicate['DescripcionErrorRegistro']

        self.create(vals)

class CheckResult(models.Model):
    _name = 'sii.check.result'
    _description = _('SII Check Result')
    _order = 'id desc'
    _rec_name = 'sii_name'

    sii_check_date = fields.Datetime(string=_('Check date'))
    sii_query_result = fields.Selection(RESULTS, string=_('Query Result'))
    sii_sender_vat = fields.Char(string=_('Sender VAT'))
    sii_sender_other_id = fields.Char(string=_('Sender Other ID'))
    sii_invoice_number = fields.Char(string=_('Invoice number'))
    sii_invoice_date = fields.Date(string=_('Invoice date'))
    sii_invoice_type = fields.Char(string=_('Invoice type'))
    sii_rectificative_type = fields.Selection([('S', _('By substitution')), ('I', _('By differences'))], string=_("Rectificative Type"))
    sii_registration_key_id = fields.Many2one('sii.reg.key', string=_("Registration key"))
    sii_amount_total = fields.Float(string=_('Amount total', digits='Account'))
    sii_description = fields.Text(string=_('Description'))
    sii_name = fields.Char(string=_('Company Name'))
    sii_partner_vat = fields.Char(string=_('Partner VAT'))
    sii_partner_other_id = fields.Char(string=_('Partner Other ID'))
    sii_presented_vat = fields.Char(string=_('Presented VAT'))
    sii_presented_datetime = fields.Datetime(string=_('Presented Datetime'))
    sii_csv = fields.Char(string=_('CSV'))
    sii_reconcile_state = fields.Selection(RECONCILE, string=_('Reconcile State'))
    sii_reconcile_datetime = fields.Datetime(string=_('Reconcile Datetime'))
    sii_reconcile_description = fields.Text(string=_('Reconcile description'))
    sii_lastime_modified = fields.Datetime(string=_('Last Time Updated'))
    sii_sent_state = fields.Char(string=_('State'))
    sii_error_code = fields.Char(string=_('Error code'))
    sii_description_error = fields.Text(string=_('Description Error'))
    sii_registry_error_description = fields.Char(string=_('Registry Error Description'))
    sii_move_id = fields.Many2one('account.move', string=_('Move'))

    def _get_data(self, record, res, model):
        data = {}
        key = ''
        key_type = ''
        if model == 'account.move':
            if record.move_type in ('out_invoice', 'out_refund'):
                data = res['RegistroRespuestaConsultaLRFacturasEmitidas'][0]
                key = 'DatosFacturaEmitida'
                key_type = 'sale'
            if record.move_type in ('in_invoice', 'in_refund'):
                data = res['RegistroRespuestaConsultaLRFacturasRecibidas'][0]
                key = 'DatosFacturaRecibida'
                key_type = 'purchase'
        return data, key, key_type

    def registry_result(self, record, res, fault, model):

        vals = {
            'sii_check_date': fields.Datetime.now()
        }
        if model == 'account.move':
            vals['sii_move_id'] = record.id
        if fault:
            vals['sii_registry_error_description'] = fault
        else:
            vals['sii_query_result'] = res['ResultadoConsulta']
            data, key, key_type = self._get_data(record, res, model)
        if 'sii_query_result' in vals and vals['sii_query_result'] == 'ConDatos':
            key_obj = self.env['sii.reg.key']
            vals['sii_sender_vat'] = data['IDFactura']['IDEmisorFactura']['NIF']
            if model == 'account.move':
                if record.move_type in ('in_invoice', 'in_refund'):
                    vals['sii_sender_other_id'] = data['IDFactura']['IDEmisorFactura']['IDOtro']
            vals['sii_invoice_number'] = data['IDFactura']['NumSerieFacturaEmisor']
            date = datetime.strptime(data['IDFactura']['FechaExpedicionFacturaEmisor'], '%d-%m-%Y')
            new_date = datetime.strftime(date, '%Y-%m-%d')
            vals['sii_invoice_date'] = new_date
            vals['sii_invoice_type'] = data[key]['TipoFactura']
            vals['sii_rectificative_type'] = data[key]['TipoRectificativa']
            registration_key = key_obj.search([('code', '=', data[key]['ClaveRegimenEspecialOTrascendencia']), ('type', '=', key_type)])
            vals['sii_registration_key_id'] = registration_key.id
            vals['sii_amount_total'] = data[key]['ImporteTotal']
            vals['sii_description'] = data[key]['DescripcionOperacion']
            if 'Contraparte' in data[key] and data[key]['Contraparte']:
                vals['sii_name'] = data[key]['Contraparte']['NombreRazon']
                vals['sii_partner_vat'] = data[key]['Contraparte']['NIF']
                vals['sii_partner_other_id'] = data[key]['Contraparte']['IDOtro']
            vals['sii_presented_vat'] = data['DatosPresentacion']['NIFPresentador']
            date = datetime.strptime(data['DatosPresentacion']['TimestampPresentacion'], '%d-%m-%Y %H:%M:%S')
            new_date = datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
            vals['sii_presented_datetime'] = new_date
            vals['sii_csv'] = data['DatosPresentacion']['CSV']
            vals['sii_reconcile_state'] = data['EstadoFactura']['EstadoCuadre']
            record.sii_reconcile_state = vals['sii_reconcile_state']
            if 'TimestampEstadoCuadre' in data['EstadoFactura']:
                if data['EstadoFactura']['TimestampEstadoCuadre']:
                    date = datetime.strptime(data['EstadoFactura']['TimestampEstadoCuadre'], '%d-%m-%Y %H:%M:%S')
                    new_date = datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
                    vals['sii_reconcile_datetime'] = new_date
            date = datetime.strptime(data['EstadoFactura']['TimestampUltimaModificacion'], '%d-%m-%Y %H:%M:%S')
            new_date = datetime.strftime(date, '%Y-%m-%d %H:%M:%S')
            vals['sii_lastime_modified'] = new_date
            vals['sii_sent_state'] = data['EstadoFactura']['EstadoRegistro']
            vals['sii_error_code'] = data['EstadoFactura']['CodigoErrorRegistro']
            vals['sii_description_error'] = data['EstadoFactura']['DescripcionErrorRegistro']
            vals['sii_reconcile_description'] = data['DatosDescuadreContraparte']

        self.create(vals)
