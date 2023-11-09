# -*- coding: utf-8 -*-

import io
import markupsafe

from odoo import models, fields, _
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

EXCEL_HEADER = [
    {
        'col2_liquidation': {'name': 'Autoliquidación', 'rowspan': 1, 'colspan': 2},
        'col3_activity': {'name': 'Actividad', 'rowspan': 1, 'colspan': 3},
        'invoice_type': {'rowspan': 2, 'colspan': 1},
        'concept': {'rowspan': 2, 'colspan': 1},
        'compute_income': {'rowspan': 2, 'colspan': 1},
        'expedition_date': {'rowspan': 2, 'colspan': 1},
        'operation_date': {'rowspan': 2, 'colspan': 1},
        'col3_identification': {'name': 'Identificación de la factura', 'rowspan': 1, 'colspan': 3},
        'col3_vat_destination': {'name': 'NIF Destinatario', 'rowspan': 1, 'colspan': 3},
        'destination_name': {'rowspan': 2, 'colspan': 1},
        'operation_key': {'rowspan': 2, 'colspan': 1},
        'operation_clasification': {'rowspan': 2, 'colspan': 1},
        'operation_exent': {'rowspan': 2, 'colspan': 1},
        'total_invoice': {'rowspan': 2, 'colspan': 1},
        'amount_base': {'rowspan': 2, 'colspan': 1},
        'tax_type': {'rowspan': 2, 'colspan': 1},
        'charged_vat': {'rowspan': 2, 'colspan': 1},
        'recharge_type': {'rowspan': 2, 'colspan': 1},
        'recharged_vat': {'rowspan': 2, 'colspan': 1},
        'col4_recieve': {'name': 'Cobro (Operación Criterio de Caja de IVA y/o artículo 7.2.1º)', 'rowspan': 1, 'colspan': 4},
        'irpf_income_tax_type': {'rowspan': 2, 'colspan': 1},
        'irpf_income_tax_amount': {'rowspan': 2, 'colspan': 1},
        'billing_agreement_registration': {'rowspan': 2, 'colspan': 1},
        'col2_property': {'name': 'Inmueble', 'rowspan': 1, 'colspan': 2},
        'external_reference': {'rowspan': 2, 'colspan': 1},
    },
    {
        'exercise': {'rowspan': 1, 'colspan': 1},
        'period': {'rowspan': 1, 'colspan': 1},
        'code': {'rowspan': 1, 'colspan': 1},
        'type': {'rowspan': 1, 'colspan': 1},
        'group': {'rowspan': 1, 'colspan': 1},
        'blank_0': {'skip': True},
        'blank_1': {'skip': True},
        'blank_2': {'skip': True},
        'blank_3': {'skip': True},
        'blank_4': {'skip': True},
        'serie': {'rowspan': 1, 'colspan': 1},
        'number': {'rowspan': 1, 'colspan': 1},
        'final_number': {'rowspan': 1, 'colspan': 1},
        'type_identification': {'rowspan': 1, 'colspan': 1},
        'country_code': {'rowspan': 1, 'colspan': 1},
        'identification': {'rowspan': 1, 'colspan': 1},
        'blank_5': {'skip': True},
        'blank_6': {'skip': True},
        'blank_7': {'skip': True},
        'blank_8': {'skip': True},
        'blank_9': {'skip': True},
        'blank_10': {'skip': True},
        'blank_11': {'skip': True},
        'blank_12': {'skip': True},
        'blank_13': {'skip': True},
        'blank_14': {'skip': True},
        'recieve_date': {'rowspan': 1, 'colspan': 1},
        'recieve_amount': {'rowspan': 1, 'colspan': 1},
        'recieve_method_used': {'rowspan': 1, 'colspan': 1},
        'recieve_id_method_used': {'rowspan': 1, 'colspan': 1},
        'blank_15': {'skip': True},
        'blank_16': {'skip': True},
        'blank_17': {'skip': True},
        'property_situation': {'rowspan': 1, 'colspan': 1},
        'property_cadastral_reference': {'rowspan': 1, 'colspan': 1},
    }
]

class SpanishBookOutReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.book.es.out.report.handler'
    _description = 'Out invoice book report'
    _inherit = 'l10n_es.generic.book.es.report.handler'


    def _get_type_book(self):
        return 'out'

    def _get_custom_valid_taxes_map(self):
        book = self.env['sii.map']._get_current_map()

        if book:
            return book._get_all_taxes('out', exclude=['SRE'])
        else:
            return []

    def _get_custom_domain(self):
        return [('move_type', 'in', ['out_invoice', 'out_refund']), ('state', '=', 'posted')]

    def _get_custom_excel_headers(self):
        return EXCEL_HEADER

    def _get_book_lines(self, options, data):
        # Overrided
        lines = []
        index = 1

        report = self.env['account.report']

        # Print first moves
        for row in data:
            operation_key = ""
            operation_clasification = ""
            for group in row.get("grouped_lines", []):
                operation_key = group.get("operation_key")
                operation_clasification = group.get("operation_clasification")
                lines.append((0, {
                    'id': report._get_generic_line_id('l10n_es.book.es.out.report.handler', index),
                    'name': '',
                    'level': 3,
                    'columns': [
                        {'name': row.get("exercise")},
                        {'name': row.get("period")[:2]},
                        {'name': row.get("activity_code")[:1]},
                        {'name': row.get("activity_type")[:2]},
                        {'name': row.get("activity_group")[:4]},
                        {'name': row.get("invoice_type")[:2]},
                        {'name': row.get("concept")[:3]},
                        {'name': report.format_value(row.get("compute_income"), blank_if_zero=True, figure_type='float')},
                        {'name': report.format_value(row.get("expedition_date"), blank_if_zero=True, figure_type='date')},
                        {'name': report.format_value(row.get("operation_date"), blank_if_zero=True, figure_type='date')},
                        {'name': row.get("serie")[:20]},
                        {'name': row.get("number")[:20]},
                        {'name': row.get("final_number")[:20]},
                        {'name': row.get("type_identification")[:2]},
                        {'name': row.get("country_code")[:2]},
                        {'name': row.get("identification")[:20]},
                        {'name': row.get("name")[:40]},
                        {'name': group.get("operation_key")[:2]},
                        {'name': group.get("operation_clasification")[:2]},
                        {'name': group.get("operation_exent")[:2]},
                        {'name': report.format_value(group.get("total_invoice"), blank_if_zero=False, figure_type='float')},
                        {'name': report.format_value(group.get("amount_base"), blank_if_zero=False, figure_type='float')},
                        {'name': report.format_value(group.get("tax_type"), blank_if_zero=False, figure_type='float')},
                        {'name': report.format_value(group.get("charged_vat"), blank_if_zero=False, figure_type='float')},
                        {'name': report.format_value(group.get("recharge_type"), blank_if_zero=True, figure_type='float')},
                        {'name': report.format_value(group.get("recharged_vat"), blank_if_zero=True, figure_type='float')},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': report.format_value(row.get("irpf_income_tax_type"), blank_if_zero=True, figure_type='float')},
                        {'name': report.format_value(row.get("irpf_income_tax_amount"), blank_if_zero=True, figure_type='float')},
                        {'name': row.get("billing_agreement_registration")[:15]},
                        {'name': row.get("property_situation")[:1]},
                        {'name': row.get("property_cadastral_reference")[:20]},
                        {'name': row.get("external_reference")[:40]},
                    ],
                    'unfoldable': False,
                    'unfolded': False,
                    'colspan': 1
                }))
                index += 1

            for payment in row.get("payment_lines", []):
                lines.append((0, {
                    'id': report._get_generic_line_id('l10n_es.book.es.out.report.handler', index),
                    'name': '',
                    'level': 3,
                    'columns': [
                        {'name': payment.get("exercise")},
                        {'name': payment.get("period")[:2]},
                        {'name': row.get("activity_code")[:1]},
                        {'name': row.get("activity_type")[:2]},
                        {'name': row.get("activity_group")[:4]},
                        {'name': row.get("invoice_type")[:2]},
                        {'name': row.get("concept")[:3]},
                        {'name': report.format_value(row.get("compute_income"), blank_if_zero=True, figure_type='float')},
                        {'name': report.format_value(row.get("expedition_date"), blank_if_zero=True, figure_type='date')},
                        {'name': row.get("")},
                        {'name': row.get("serie")[:20]},
                        {'name': row.get("number")[:20]},
                        {'name': row.get("final_number")[:20]},
                        {'name': row.get("type_identification")[:2]},
                        {'name': row.get("country_code")[:2]},
                        {'name': row.get("identification")[:20]},
                        {'name': row.get("name")[:40]},
                        {'name': operation_key[:2]},
                        {'name': operation_clasification[:2]},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': report.format_value(payment.get("recieve_date"), blank_if_zero=True, figure_type='date')},
                        {'name': report.format_value(payment.get("recieve_amount"), blank_if_zero=False, figure_type='float')},
                        {'name': payment.get("recieve_method_used")[:2]},
                        {'name': payment.get("recieve_id_method_used")[:34]},
                        {'name': report.format_value(row.get("irpf_income_tax_type"), blank_if_zero=True, figure_type='float')},
                        {'name': report.format_value(row.get("irpf_income_tax_amount"), blank_if_zero=True, figure_type='float')},
                        {'name': row.get("billing_agreement_registration")[:15]},
                        {'name': row.get("")},
                        {'name': row.get("")},
                        {'name': row.get("")},
                    ],
                    'unfoldable': False,
                    'unfolded': False,
                    'colspan': 1
                }))
                index += 1

        return lines
