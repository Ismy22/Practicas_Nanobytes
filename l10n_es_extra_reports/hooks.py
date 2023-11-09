# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

from odoo import api, SUPERUSER_ID, models, _
from odoo.http import request

def post_extra_reports_sequences(cr, registry):
    """ 
        Since our new fields for mod303 go to the end when create we should resequence all lines to move them above 66
    """
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        mod303_report_id = env.ref("l10n_es_reports.mod_303").id

        cr.execute("""
            UPDATE account_report_line
            SET sequence = id
            WHERE report_id = %d
        """ % mod303_report_id)

        result_line = env.ref("l10n_es_reports.mod_303_title_18")
        good_sequence = result_line.sequence

        arr_nmod303_fields = []
        arr_nmod303_fields.append(str(env.ref("l10n_es_extra_reports.nmod_303_casilla_76").id))
        arr_nmod303_fields.append(str(env.ref("l10n_es_extra_reports.nmod_303_casilla_64").id))
        nmod303_fields = ", ".join(arr_nmod303_fields)

        cr.execute("""
            UPDATE account_report_line
            SET sequence = %d
            WHERE id in (%s)
        """ % (good_sequence, nmod303_fields))
        
    except Exception as e:
        _logger.warning(_("There was an error trying to resequence mod303 ..."))
        pass