# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime, date

import logging
_logger = logging.getLogger(__name__)

class Company(models.Model):
    _inherit = 'res.company'

    # AEAT
    activity = fields.Char(string=_("Activity"), help=_("To comply with articles 40.1, 47.2, 51 quater and 61.2 of the RIVA and article 9.4 of Order HAC/773/2019, the activity to which the entry corresponds will be distinguished. Used from move > journal > company. Example: A036533"))
    billing_agreement_registration = fields.Char(string=_("Billing Agreement Registration"), help=_("The authorization registration number (“RGE############”) obtained at the Agency's"))

    # SII
    is_sii_active = fields.Boolean(string=_('Activate SII'))
    sii_agency_id = fields.Many2one('sii.agency', string=_("Agency"), default=lambda self: self.env.ref('l10n_es_extra_reports.sii_agency_at', raise_if_not_found=False))
    is_sii_test = fields.Boolean(string=_('Is SII for test?'))
    is_sii_description_automatic = fields.Boolean(string=_("Is SII description automatic?"), default=False, help=_("If description automatic is checked then description of invoice will be filled automatically with the description of lines"))
    sii_description = fields.Char(string=_("SII Description"))
    sii_description_sale = fields.Char(string=_("SII Sale Description"))
    sii_description_purchase = fields.Char(string=_("SII Purchase Description"))
    sii_send_moves_on = fields.Selection(string=_("Send SII Invoice On"), selection=[('validate', _('Validate')), ('button', _('Button'))], default='button')
    use_queue = fields.Boolean(string=_("Use queue"), help=_("If check it use queue_job module"))
    sii_send_moves_time = fields.Selection(string=_("Send SII Invoice Time"), selection=[('auto', _('On validate')), ('fixed', _('At fixed time')), ('delayed', _('With delay'))], default='auto')
    sii_sent_time = fields.Float(string=_("Which hour?"))
    sii_delay_time = fields.Float(string=_("How much delay?"))

    sii_activity_type_id = fields.Many2one('mail.activity.type', string=_("SII Activity Type"))
    sii_activity_user_id = fields.Many2one('res.users', string=_("SII Activity User"))

    def _get_time(self):
        if self.sii_send_moves_time == 'delayed':
            return datetime.now() + timedelta(seconds=self.delay_time * 3600)
        if self.sii_send_moves_time == 'fixed':
            now = datetime.now()

            hour, minute = divmod(self.sent_time, 1)
            hour = int(hour)
            minute = int(minute*60)

            if now.hour > hour or (now.hour == hour and now.minute > minute):
                now += timedelta(days=1)

            return now.replace(hour=hour, minute=minute)

        return None
