# -*- coding: utf-8 -*-

import markupsafe

from odoo import models, fields, _
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

ORDER_COLUMNS = {
    0: 'id',
    1: 'anio',
    2: 'clave',
    3: 'nif_partner',
    4: 'provincia',
    5: 'rend_dinerario',
    6: 'porcentaje',
    7: 'cuota_dineraria'
}

class SpanishMod190TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod190.tax.report.handler'
    _description = 'Tax Report (Mod 190)'
    _inherit = 'account.report.custom.handler'

    def _query_mod_190(self, options):

        where_cond = ""
        if options.get("date", {}):
            op_date = options.get("date", {})
            if op_date.get("date_from", False) and op_date.get("date_to", False):
                where_cond += " and aml.date >= '" + op_date.get("date_from", False) + "' and aml.date <= '" + op_date.get("date_to", False) + "' " 

        if self.env.companies:
            where_cond += " and aml.company_id in (" + ', '.join([str(c) for c in self.env.companies.ids]) + ") "

        if options.get("journals", []):
            journals = options.get("journals", [])
            journal_ids = []

            for journal in journals:
                if journal.get("selected", False):
                    journal_ids.append(journal.get("id"))

            if journal_ids:
                where_cond += " and journal_id in (" + ', '.join([str(j) for j in journal_ids]) + ") "

        order_by = ""
        if options.get('order_column'):
            order_by = " order by " + str(ORDER_COLUMNS.get(abs(options.get('order_column'))))
            if options.get('order_column') > 0:
                order_by += " ASC "
            else:
                order_by += " DESC "

        sql = """drop view if exists modelo_190_report;
            create view modelo_190_report as (
                with consulta as(

                    with impuestos_irpf as(
                        select
                            distinct(invoice_tax_id) as account_tax_id
                        from
                            account_tax_repartition_line
                        where id in (
                        select 
                            account_tax_repartition_line_id
                        from
                            account_account_tag_account_tax_repartition_line_rel
                        where
                            account_account_tag_id in (select id from account_account_tag where name ilike 'mod111%')
                        ) and invoice_tax_id is not null
                        union
                        select
                            distinct(refund_tax_id) as account_tax_id
                        from
                            account_tax_repartition_line
                        where id in (
                        select 
                            account_tax_repartition_line_id
                        from
                            account_account_tag_account_tax_repartition_line_rel
                        where
                            account_account_tag_id in (select id from account_account_tag where name ilike 'mod111%')
                        ) and refund_tax_id is not null
                    ),
                    datos_111 as
                    (
                        select extract(year from date) as anio, partner_id, 'base' as tipo, account_tax_id as tax_id, sum(balance) as balance 
                        from account_move_line aml 
                        inner join account_move_line_account_tax_rel amlatr on (aml.id = amlatr.account_move_line_id) 
                        where account_tax_id in (select account_tax_id from impuestos_irpf) """ + where_cond + """ 
                        group by account_tax_id, partner_id, anio
                    union
                        select extract(year from date) as anio, partner_id, 'cuota' as tipo, tax_line_id as tax_id, sum(balance) as balance 
                        from account_move_line aml 
                        where tax_line_id in (select account_tax_id from impuestos_irpf) """ + where_cond + """ 
                        group by tax_line_id, partner_id, anio
                    )

                    select
                    cast (anio as text) as anio,
                    (case when exists(  select
                        distinct(invoice_tax_id) as account_tax_id
                    from
                        account_tax_repartition_line
                    where id in (
                        select 
                            account_tax_repartition_line_id
                        from 
                            account_account_tag_account_tax_repartition_line_rel 
                        where 
                            account_account_tag_id = (select id from account_account_tag where name = 'mod111[02]')
                    ) and invoice_tax_id = d.tax_id
                    union
                    select
                        distinct(refund_tax_id) as account_tax_id
                    from
                        account_tax_repartition_line
                    where id in (
                        select 
                            account_tax_repartition_line_id
                        from 
                            account_account_tag_account_tax_repartition_line_rel 
                        where 
                            account_account_tag_id = (select id from account_account_tag where name = 'mod111[02]')
                    ) and invoice_tax_id = d.tax_id) then 'A'
                    else 'G - 01'
                    end) as clave,
                    (select name from res_partner where id = partner_id) as name_partner,
                    (select vat from res_partner where id = partner_id) as nif_partner,
                    (select name from res_country_state where id = (select state_id from res_partner where id = partner_id)) as provincia,
                    sum((case when tipo = 'base' then balance
                    else 0
                    end)) as rend_dinerario,
                    (select -amount from account_tax where id = d.tax_id) as porcentaje,
                    sum((case when tipo = 'cuota' then -balance
                    else 0
                    end)) as cuota_dineraria
                    from datos_111 d group by anio, partner_id, clave, tax_id

                )
                select  ROW_NUMBER() over (order by consulta.anio::text, consulta.name_partner)as id, * from consulta            );
            select * from modelo_190_report """ + order_by + """;"""

        self._cr.execute(sql)

        return self._cr.fetchall()

    def _get_mod_190_line(self, options, row):
        report = self.env['account.report']
        return {
            'id': report._get_generic_line_id('modelo.190.report', row[0]),
            'name': row[3],
            'level': 3,
            'columns': [
                {'name': str(row[1]), 'style': 'text-align: center'},
                {'name': str(row[2]), 'style': 'text-align: center'},
                {'name': str(row[4]), 'style': 'text-align: left'},
                {'name': str(row[5]), 'style': 'text-align: left'},
                {'name': report.format_value(row[6], blank_if_zero=False, figure_type='monetary')},
                {'name': report.format_value(row[7], blank_if_zero=False, figure_type='percentage')},
                {'name': report.format_value(row[8], blank_if_zero=False, figure_type='monetary')},
            ],
            'unfoldable': False,
            'unfolded': False,
            'colspan': 1
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        query_res = self._query_mod_190(options)

        lines = []
        for row in query_res:
            lines.append(self._get_mod_190_line(options, row))

        return [(0, line) for line in lines]
