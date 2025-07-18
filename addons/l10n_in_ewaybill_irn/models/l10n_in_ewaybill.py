# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_in_ewaybill.tools.ewaybill_api import EWayBillApi, EWayBillError


class L10nInEwaybill(models.Model):

    _inherit = 'l10n.in.ewaybill'

    is_process_through_irn = fields.Boolean(compute='_compute_is_process_through_irn')
    is_sent_through_irn = fields.Boolean(readonly=True)

    @api.depends('account_move_id.l10n_in_edi_status')
    def _compute_is_process_through_irn(self):
        for ewaybill in self:
            account_move_id = ewaybill.account_move_id
            ewaybill.is_process_through_irn = (
                account_move_id
                # E-way Bill is not generated by IRN for document types of Debit Note and Credit Note.
                and not (account_move_id.move_type == 'out_refund' or account_move_id.debit_origin_id)
                and account_move_id.l10n_in_edi_status == 'sent'
            )

    def _prepare_ewaybill_transportation_json_payload(self):
        if self.is_process_through_irn:
            return dict(
                filter(lambda kv: kv[1], {
                    "TransId": self.transporter_id.vat,
                    "TransName": self.transporter_id.name,
                    "TransMode": self.mode,
                    "TransDocNo": self.transportation_doc_no,
                    "TransDocDt": self.transportation_doc_date and self.transportation_doc_date.strftime("%d/%m/%Y"),
                    "VehNo": self.vehicle_no,
                    "VehType": self.vehicle_type,
                }.items())
            )
        return super()._prepare_ewaybill_transportation_json_payload()

    def _ewaybill_generate_irn_json(self):
        json_payload = {
            'Irn': self.account_move_id._get_l10n_in_edi_response_json().get('Irn'),
            'Distance': str(self.distance),
            **self._prepare_ewaybill_transportation_json_payload(),
            'DispDtls': self.env['account.move']._get_l10n_in_edi_partner_details(
                self.partner_ship_from_id, set_phone_and_email=False, set_vat=False)
        }
        if self.account_move_id.l10n_in_gst_treatment == 'overseas':
            json_payload["ExpShipDtls"] = self.env['account.move']._get_l10n_in_edi_partner_details(
                self.partner_ship_to_id, set_phone_and_email=False, set_vat=False)
            json_payload["ExpShipDtls"].pop('Nm')  # 'Nm'(Name) is not included in ExpShipDtls as per the JSON schema
        return json_payload

    def _compute_content(self):
        irn_ewaybill = self.filtered('is_process_through_irn')
        for ewaybill in irn_ewaybill:
            ewaybill_json = ewaybill._ewaybill_generate_irn_json()
            ewaybill.content = base64.b64encode(json.dumps(ewaybill_json).encode())
        super(L10nInEwaybill, self - irn_ewaybill)._compute_content()

    def action_generate_ewaybill(self):
        irn_ewaybill = self.filtered('is_process_through_irn')
        for ewaybill in irn_ewaybill:
            if errors := ewaybill._check_configuration():
                raise UserError('\n'.join(errors))
            ewaybill._generate_ewaybill_by_irn()
        super(L10nInEwaybill, self - irn_ewaybill).action_generate_ewaybill()

    def action_reset_to_pending(self):
        res = super().action_reset_to_pending()
        self.is_sent_through_irn = False
        return res

    def _generate_ewaybill_by_irn(self):
        self.ensure_one()
        self._lock_ewaybill()
        try:
            response = self._ewaybill_generate_by_irn(self._ewaybill_generate_irn_json())
        except EWayBillError as error:
            self._handle_error(error)
            return False
        self._handle_internal_warning_if_present(response)  # In case of error 604
        response_data = response.get('data', {})
        name = response_data.get('EwbNo')
        self._create_and_post_response_attachment(name, response)
        # Note: response keys are different then the direct one
        self._write_successfully_response({
            'name': name,
            'state': 'generated',
            'is_sent_through_irn': True,
            'ewaybill_date': self._convert_str_datetime_to_date(
                response_data['EwbDt']
            ),
            'ewaybill_expiry_date': self._convert_str_datetime_to_date(
                response_data.get('EwbValidTill')
            ),
            **self._l10n_in_ewaybill_handle_zero_distance_alert_if_present(response_data)
        })
        self.env.cr.commit()

    def _get_edi_irn_number(self):
        self.ensure_one()
        l10n_in_edi_response_json = self.account_move_id._get_l10n_in_edi_response_json()
        if not l10n_in_edi_response_json:
            raise EWayBillError({
                'error': [{
                    'code': 'waiting',
                    'message': self.env._("waiting for IRN generation to create E-waybill")
                }]
            })
        return l10n_in_edi_response_json['Irn']

    def _ewaybill_generate_by_irn(self, json_payload):
        self.ensure_one()
        if not self.company_id._l10n_in_edi_get_token():
            raise EWayBillError({
                'error': [{
                    'code': '0',
                    'message': self.env._(
                        "Unable to send E-waybill by IRN."
                        "Ensure GST Number set on company setting and EDI and Ewaybilll"
                        " credentials are Verified."
                    )
                }]
            })
        response = self.account_move_id._l10n_in_edi_connect_to_server(
            url_end_point='generate_ewaybill_by_irn',
            json_payload=json_payload
        )
        if response.get('error'):
            error_codes = [error.get('code') for error in response.get('error')]
            if 'no-credit' in error_codes:
                response['odoo_warning'].append({
                    'message': self.env['account.move']._l10n_in_edi_get_iap_buy_credits_message()
                })
            if '4002' in error_codes or '4026' in error_codes:
                # Get E-waybill by details in case of IRN is already generated
                # this happens when timeout from the Government portal but E-waybill is generated
                response = self.account_move_id._l10n_in_edi_connect_to_server(
                    url_end_point='get_ewaybill_by_irn',
                    params={"irn": self._get_edi_irn_number()}
                )
                response.update({
                    'odoo_warning': [{
                        'message': self._get_default_help_message(self.env._('generated')),
                        'message_post': True
                    }]
                })
            if response.get('error'):
                raise EWayBillError(response)
        return response
