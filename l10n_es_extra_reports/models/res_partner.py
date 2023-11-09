# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


DOCUMENTATION_TYPE = [
    ('02', _("NIF/IVA")), 
    ('03', _("Passport")), 
    ('04', _("Official identification issued by the country or territory of residence")), 
    ('05', _("Residence certificate")), 
    ('06', _("Other document")),
    ('07', _("Not registered"))
]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_es_reports_documentation_type = fields.Selection(string=_("Documentation Type"), selection=DOCUMENTATION_TYPE, default='02')
    anonymous_customer = fields.Boolean(string=_("Anonymous customer"))

    @api.constrains('vat', 'country_id')
    def check_vat(self):
        # Overrided function to check validation one by one
        # The context key 'no_vat_validation' allows you to store/set a VAT number without doing validations.
        # This is for API pushes from external platforms where you have no control over VAT numbers.
        if self.env.context.get('no_vat_validation'):
            return

        for partner in self:
            # Skip checks when only one character is used. Some users like to put '/' or other as VAT to differentiate between
            # A partner for which they didn't input VAT, and the one not subject to VAT
            if not partner.vat or len(partner.vat) == 1:
                continue
            # Skip when documention type is different from iva/
            if partner.l10n_es_reports_documentation_type != '02':
                continue
            country = partner.commercial_partner_id.country_id
            if self._run_vat_test(partner.vat, country, partner.is_company) is False:
                partner_label = _("partner [%s]", partner.name)
                msg = partner._build_vat_error_message(country and country.code.lower() or None, partner.vat, partner_label)
                raise ValidationError(msg)