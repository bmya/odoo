# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"


    @api.model
    def _l10n_cl_get_demo_data_res_partner(self, company=False):
        return {
            'demo_partner_4': {
                'name': 'Moher Solutions S.A.',
                'l10n_latam_identification_type_id': 'l10n_cl.it_RUT',
                'l10n_cl_sii_taxpayer_type': '1',
                'vat': '77594500-1',
                'street': 'Paseo La Ventana 8888',
                'city': 'Pedro Aguirre Cerda',
                'state_id': 'base.state_cl_13',
                'country_id': 'base.cl',
                'email': 'info@mohersolutions.com',
            },
            'demo_partner_5': {
                'name': 'Modulus SpA',
                'l10n_latam_identification_type_id': 'l10n_cl.it_RUT',
                'vat': '76202517-5',
                'street': 'Carpe Diem 3333',
                'city': 'Vitacura',
                'state_id': 'base.state_cl_13',
                'country_id': 'base.cl',
                'email': 'modulus@modulusspa.com',
            },
            'demo_partner_6': {
                'name': 'La Misión S.A.',
                'l10n_latam_identification_type_id': 'l10n_cl.it_RUT',
                'vat': '76204900-7',
                'street': 'El Arauco 1111',
                'city': 'Providencia',
                'state_id': 'base.state_cl_13',
                'country_id': 'base.cl',
                'email': 'mision@example.com',
            },
            # Partner for fee receipts
            'res_partner_fee_receipts': {
                'name': 'Roberto Norambuena González',
                'l10n_latam_identification_type_id': 'l10n_cl.it_RUT',
                'l10n_cl_sii_taxpayer_type': '2',
                'vat': '13009922-K',
                'zip': '7658389',
                'street': 'La Calle Yanquihue 2020',
                'city': 'Santiago',
                'state_id': 'base.state_cl_13',
                'country_id': 'base.cl',
                'email': 'RNG@example.com',
            },
        }

    @api.model
    def _l10n_cl_get_demo_data_move(self, company=False):
        company_id = company.id or self.env.company.id
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'CL':
            foreign_invoice = self.env.ref('l10n_cl.dc_fe_dte').id
            foreign_credit_note = self.env.ref('l10n_cl.dc_ncex_dte').id
            purchase_journal = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company_id),
                    ('type', '=', 'purchase')
                ], limit=1)
            purchase_journal.l10n_latam_use_documents = True
            test_partners_foreign = self.env['res.partner'].search([('name', 'in', ['Deco Addict', 'Azure Interior'])])
            test_partners_foreign |= (self.env.ref('base.res_partner_2') | self.env.ref('base.res_partner_12'))
            test_partners_foreign.write({'l10n_sii_taxpayer_type': '4'})
            move_data['demo_invoice_1']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_2']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_3']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_invoice_followup']['l10n_latam_document_type_id'] = foreign_invoice
            move_data['demo_move_auto_reconcile_1']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_2']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_5']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_6']['l10n_latam_document_type_id'] = foreign_credit_note
            move_data['demo_move_auto_reconcile_7']['l10n_latam_document_type_id'] = foreign_credit_note
        return move_data

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company=company)
        if company.account_fiscal_country_id.code == 'CL':
            demo_data['res.partner'] = self._l10n_cl_get_demo_data_res_partner(company)
            demo_data['account.move'] |= self._l10n_cl_get_demo_data_move(company)
        return demo_data

    # @api.model
    # def _l10n_cl_get_demo_data_move_reversal(self, company=False):
    #     cid = company.id or self.env.company.id
    #     sale_journal = self.env['account.journal'].search(
    #         domain=[
    #             *self.env['account.journal']._check_company_domain(company_id),
    #             ('type', '=', 'sale')
    #         ], limit=1,
    #     )
    #     purchase_journal = self.env['account.journal'].search(
    #         domain=[
    #             *self.env['account.journal']._check_company_domain(company_id),
    #             ('type', '=', 'purchase')
    #         ], limit=1,
    #     )
    #     ref = self.env.ref
    #     move_data = super()._get_demo_data_move(company)
    #     if company.account_fiscal_country_id.code == "CL":
    #         foreign_invoice = self.env.ref('l10n_cl.dc_fe_dte').id
    #         foreign_credit_note = self.env.ref('l10n_cl.dc_ncex_dte').id
    #         domestic_invoice = self.env.ref('l10n_cl.dc_a_f_dte').id
    #         domestic_credit_note = self.env.ref('l10n_cl.dc_nc_dte').id
    #         domestic_debit_note = self.env.ref('l10n_cl.dc_nd_dte').id
    #         receipt = self.env.ref('l10n_cl.dc_b_f_dte').id
    #         purchase_journal = self.env['account.journal'].search([
    #             *self.env['account.journal']._check_company_domain(company),
    #             ('type', '=', 'purchase'),
    #             ('l10n_latam_use_documents', '=', True),
    #         ]).l10n_latam_use_documents = True
#
    #         move_data.update({
    #             # Create draft refund for invoice 3
    #             'demo_refund_invoice_1': {
    #                 'reason': 'Venta Cancelada',
    #                 'move_ids': 'demo_invoice_1',
    #                 'journal_id': sale_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             # Create draft refund for invoice 4
    #             'demo_refund_invoice_2': {
    #                 'reason': 'Venta Cancelada',
    #                 'move_ids': 'demo_invoice_4',
    #                 'l10n_latam_document_type_id': domestic_invoice,
    #                 'journal_id': sale_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             'demo_refund_invoice_3': {
    #                 'reason': 'Venta Cancelada',
    #                 'move_ids': 'demo_invoice_5',
    #                 'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
    #                 'journal_id': sale_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             'demo_refund_invoice_4': {
    #                 'reason': 'Venta Cancelada',
    #                 'move_ids': 'demo_invoice_6',
    #                 'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
    #                 'journal_id': sale_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             # Account supplier refund
    #             'demo_sup_refund_invoice_3': {
    #                 'reason': 'Mercadería defectuosa',
    #                 'l10n_latam_document_number': 'BB0123456',
    #                 'move_ids': 'demo_sup_invoice_1',
    #                 'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv',
    #                 'journal_id': purchase_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             'demo_sup_refund_invoice_2': {
    #                 'reason': 'Venta cancelada',
    #                 'l10n_latam_document_number': 'BB0123457',
    #                 'move_ids': 'demo_sup_invoice_2',
    #                 'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
    #                 'journal_id': purchase_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #             'demo_sup_refund_invoice_1': {
    #                 'reason': 'Venta cancelada',
    #                 'l10n_latam_document_number': 'BB0123458',
    #                 'move_ids': 'demo_sup_invoice_7',
    #                 'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
    #                 'journal_id': purchase_journal.id,
    #                 'date': time.strftime('%Y-%m') + '-01'
    #             },
    #         })
    #         return move_data

#    def _post_load_demo_data(self, company=False):
#        if company.account_fiscal_country_id.code != "CL":
#            return super()._post_load_demo_data(company)
#        invoices = (
#            self.env.ref('demo_invoice_1')
#            + self.env.ref('demo_invoice_2')
#            + self.env.ref('demo_invoice_3')
#            + self.env.ref('demo_invoice_4')
#            + self.env.ref('demo_invoice_5')
#            + self.env.ref('demo_invoice_6')
#            + self.env.ref('demo_invoice_8')
#            + self.env.ref('demo_invoice_9')
#            + self.env.ref('demo_sup_invoice_1')
#            + self.env.ref('demo_sup_invoice_2')
#            + self.env.ref('demo_sup_invoice_3')
#            + self.env.ref('demo_sup_invoice_6')
#            + self.env.ref('demo_sup_invoice_7')
#            + self.env.ref('demo_sup_invoice_8')
#            + self.env.ref('demo_sup_invoice_9')
#        )
#        # the invoice_extract acts like a placeholder for the OCR to be ran and
#        # doesn't contain any lines yet
#        for move in invoices:
#            try:
#                move.action_post()
#            except (UserError, ValidationError):
#                _logger.exception('Error while posting invoices')
#
#        # Post the reversal moves
#        invoices_to_revert = (
#            self.env.ref('demo_refund_invoice_1')
#            + self.env.ref('demo_refund_invoice_2')
#            + self.env.ref('demo_refund_invoice_3')
#            + self.env.ref('demo_refund_invoice_4')
#            + self.env.ref('demo_sup_refund_invoice_3')
#            + self.env.ref('demo_sup_refund_invoice_2')
#        )
#        for move in invoices_to_revert:
#            try:
#                self.env['account.move'].browse(move.refund_moves().get('res_id')).action_post()
#            except (UserError, ValidationError):
#                _logger.exception('Error while posting reversal moves')
#