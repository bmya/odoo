# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_latam_document_type_id_code = fields.Char(related='l10n_latam_document_type_id.code', string='Doc Type')
    partner_id_vat = fields.Char(related='partner_id.vat', string='VAT No')

    def get_document_type_sequence(self):
        """ Return the match sequences for the given journal and invoice """
        self.ensure_one()
        if self.journal_id.l10n_latam_use_documents and self.l10n_latam_country_code == 'CL':
            res = self.journal_id.l10n_cl_sequence_ids.filtered(
                lambda x: x.l10n_latam_document_type_id == self.l10n_latam_document_type_id)
            return res
        return super().get_document_type_sequence()

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        domain += [('active', '=', True)]
        if (self.journal_id.l10n_latam_use_documents and
                self.journal_id.company_id.country_id == self.env.ref('base.cl')):
            account_move_type = self._context.get('default_type') or self.type
            # if account_move_type in ['in_invoice', 'out_invoice']:
            #     seq = self.journal_id.l10n_cl_sequence_ids
            # else:
            #     seq = self.journal_id.refund_sequence_id
            # domain = [('id', '=', seq.l10n_latam_document_type_id.id)]
        return domain



