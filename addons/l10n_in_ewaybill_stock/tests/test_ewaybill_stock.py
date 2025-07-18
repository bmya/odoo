from freezegun import freeze_time

from odoo import _
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestStockEwaybill(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref('stock.group_stock_manager')
        cls.product_a.standard_price = 500.00
        cls.partner_a.write({
            'vat': '27DJMPM8965E1ZE',
            'l10n_in_gst_treatment': 'regular',
            'state_id': cls.state_in_mh.id,
            'zip': '431122'
        })

    def _create_stock_picking(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        delivery_picking = self.env['stock.picking'].create({
            'partner_id': self.partner_a.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'quantity': 5,
                'location_id': self.env.ref('stock.stock_location_customers').id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })]
        })
        delivery_picking.button_validate()
        return delivery_picking

    @freeze_time('2024-04-26')
    def test_ewaybill_stock(self):
        delivery_picking = self._create_stock_picking()
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'picking_id': delivery_picking.id,
            'mode': False,
            'type_id': self.env.ref('l10n_in_ewaybill_stock.type_delivery_challan_sub_line_sales').id,
        })
        self.assertRecordValues(ewaybill, [{
            'state': 'pending',
            'display_name': _('Pending'),
            'fiscal_position_id': self.fp_in_inter_state.id,
        }])
        ewaybill.fiscal_position_id = self.fp_in_inter_state
        self.assertEqual(ewaybill.move_ids[0].ewaybill_tax_ids, self.igst_sale_5)
        expected_json = {
            'supplyType': 'O',
            'subSupplyType': '10',
            'docType': 'CHL',
            'transactionType': 1,
            'transDistance': '0',
            'docNo': 'compa/OUT/00001',
            'docDate': '26/04/2024',
            'fromGstin': '24AAGCC7144L6ZE',
            'toGstin': '27DJMPM8965E1ZE',
            'fromTrdName': 'Default Company',
            'toTrdName': 'Partner Intra State',
            'fromStateCode': 24,
            'toStateCode': 27,
            'fromAddr1': 'Khodiyar Chowk',
            'toAddr1': 'Karansinhji Rd',
            'fromAddr2': 'Sala Number 3',
            'toAddr2': 'Karanpara',
            'fromPlace': 'Amreli',
            'toPlace': 'Rajkot',
            'fromPincode': 365220,
            'toPincode': 431122,
            'actToStateCode': 27,
            'actFromStateCode': 24,
            'itemList': [{
                'productName': 'product_a',
                'hsnCode': '111111',
                'productDesc': 'product_a',
                'quantity': 5.0,
                'qtyUnit': 'UNT',
                'taxableAmount': 2500.0,
                'igstRate': 5.0,
            }],
            'totalValue': 2500.0,
            'cgstValue': 0.0,
            'sgstValue': 0.0,
            'igstValue': 125.0,
            'cessValue': 0.0,
            'cessNonAdvolValue': 0.0,
            'otherValue': 0.0,
            'totInvValue': 2625.0
        }
        self.assertDictEqual(ewaybill._ewaybill_generate_direct_json(), expected_json)

    @freeze_time('2024-04-26')
    def test_ewaybill_stock_test_2(self):
        """
        Ewaybill challan type other test with description
        """
        delivery_picking = self._create_stock_picking()
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'picking_id': delivery_picking.id,
            'transporter_id': self.partner_a.id,
            'mode': False,
            'type_id': self.env.ref('l10n_in_ewaybill_stock.type_delivery_challan_sub_others').id,
            'type_description': "Other reasons"
        })
        expected_json = {
          'supplyType': 'O',
          'subSupplyType': '8',
          'subSupplyDesc': 'Other reasons',
          'docType': 'CHL',
          'transactionType': 1,
          'transDistance': '0',
          'docNo': 'compa/OUT/00002',
          'docDate': '26/04/2024',
          'fromGstin': '24AAGCC7144L6ZE',
          'toGstin': '27DJMPM8965E1ZE',
          'fromTrdName': 'Default Company',
          'toTrdName': 'Partner Intra State',
          'fromStateCode': 24,
          'toStateCode': 27,
          'fromAddr1': 'Khodiyar Chowk',
          'toAddr1': 'Karansinhji Rd',
          'fromAddr2': 'Sala Number 3',
          'toAddr2': 'Karanpara',
          'fromPlace': 'Amreli',
          'toPlace': 'Rajkot',
          'fromPincode': 365220,
          'toPincode': 431122,
          'actToStateCode': 27,
          'actFromStateCode': 24,
          'transporterId': '27DJMPM8965E1ZE',
          'transporterName': 'Partner Intra State',
          'itemList': [
            {
              'productName': 'product_a',
              'hsnCode': '111111',
              'productDesc': 'product_a',
              'quantity': 5.0,
              'qtyUnit': 'UNT',
              'taxableAmount': 2500.0,
              'igstRate': 5.0
            }
          ],
          'totalValue': 2500.0,
          'cgstValue': 0.0,
          'sgstValue': 0.0,
          'igstValue': 125.0,
          'cessValue': 0.0,
          'cessNonAdvolValue': 0.0,
          'otherValue': 0.0,
          'totInvValue': 2625.0
        }
        self.assertDictEqual(ewaybill._ewaybill_generate_direct_json(), expected_json)
