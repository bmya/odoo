# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestBatchPicking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Create 3 standard pickings and reserve them to have some move lines.
        The setup data looks like this:
        Picking1                Picking2                Picking3
            ProductA                ProductA                ProductB
                Lot1: 5 units           Lot4: 5 units           SN6 : 1 unit
                Lot2: 5 units                                   SN7 : 1 unit
                Lot3: 5 units                                   SN8 : 1 unit
            ProductB                                            SN9 : 1 unit
                SN1 : 1 unit                                    SN10: 1 unit
                SN2 : 1 unit
                SN3 : 1 unit
                SN4 : 1 unit
                SN5 : 1 unit
        The picking_internal is the same as Picking1 move-wise, only using a different picking_type so it doesn't get auto-batched with the other pickings.
        """
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.picking_type_out = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_out')
        cls.picking_type_in = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_in')
        cls.picking_type_internal = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_internal')
        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])

        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.lots_p_a = cls.env['stock.lot'].create([{
            'name': 'lot_product_a_' + str(i + 1),
            'product_id': cls.productA.id,
        } for i in range(4)])
        cls.productB = cls.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'tracking': 'serial',
        })
        cls.lots_p_b = cls.env['stock.lot'].create([{
            'name': 'lot_product_a_' + str(i + 1),
            'product_id': cls.productB.id,
        } for i in range(10)])

        Quant = cls.env['stock.quant']
        for lot in cls.lots_p_a:
            Quant._update_available_quantity(cls.productA, cls.stock_location, 5.0, lot_id=lot)
        for lot in cls.lots_p_b:
            Quant._update_available_quantity(cls.productB, cls.stock_location, 1.0, lot_id=lot)

        cls.picking_client_1 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
            'state': 'draft',
        })

        cls.env['stock.move'].create({
            'product_id': cls.productA.id,
            'product_uom_qty': 15,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_1.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.env['stock.move'].create({
            'product_id': cls.productB.id,
            'product_uom_qty': 5,
            'product_uom': cls.productB.uom_id.id,
            'picking_id': cls.picking_client_1.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_client_2 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
            'state': 'draft',
        })

        cls.env['stock.move'].create({
            'product_id': cls.productA.id,
            'product_uom_qty': 5,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_2.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_client_3 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
            'state': 'draft',
        })

        cls.env['stock.move'].create({
            'product_id': cls.productB.id,
            'product_uom_qty': 5,
            'product_uom': cls.productB.uom_id.id,
            'picking_id': cls.picking_client_3.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_internal = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_internal,
            'company_id': cls.env.company.id,
            'state': 'draft',
        })

        cls.env['stock.move'].create({
            'product_id': cls.productA.id,
            'product_uom_qty': 15,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_internal.id,
            'location_id': cls.customer_location.id,
            'location_dest_id': cls.stock_location.id,
        })

        cls.env['stock.move'].create({
            'product_id': cls.productB.id,
            'product_uom_qty': 5,
            'product_uom': cls.productB.uom_id.id,
            'picking_id': cls.picking_internal.id,
            'location_id': cls.customer_location.id,
            'location_dest_id': cls.stock_location.id,
        })

        cls.all_pickings = cls.picking_client_1 | cls.picking_client_2 | cls.picking_client_3
        cls.all_pickings.action_confirm()
        cls.picking_internal.action_confirm()

    def test_creation_from_lines(self):
        """ Select all the move_lines and create a wave from them """
        all_lines = self.all_pickings.move_line_ids
        res_dict = all_lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': all_lines.ids}
        self.assertEqual(res_dict.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertTrue(wave)
        self.assertEqual(wave.picking_ids, self.all_pickings)
        self.assertEqual(wave.move_line_ids, all_lines)
        self.assertEqual(wave.user_id, self.user_demo)

    def test_creation_from_pickings(self):
        """ Select all the picking_ids and create a wave from them """
        action = self.env['ir.actions.actions']._for_xml_id('stock_picking_batch.stock_add_to_wave_action_stock_picking')
        action['context'] = {'active_model': 'stock.picking', 'active_ids': self.all_pickings.ids}
        self.assertEqual(action.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, action)
        wizard_form.mode = 'new'
        wizard = wizard_form.save()
        res = wizard.attach_pickings()
        self.assertEqual(set(res['context']['picking_to_wave']), set(self.all_pickings.ids))

    def test_add_to_existing_wave_from_lines(self):
        res_dict = self.picking_client_1.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_1.move_line_ids.ids}
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        wizard_form.save().attach_pickings()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])

        res_dict = self.picking_client_2.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_2.move_line_ids.ids}
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'existing'
        wizard_form.wave_id = wave
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertEqual(len(wave), 1)
        self.assertEqual(wave.picking_ids, self.picking_client_1 | self.picking_client_2)

    def test_add_to_existing_wave_from_pickings(self):
        res_dict = self.picking_client_1.move_line_ids.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': self.picking_client_1.move_line_ids.ids}
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.user_id = self.user_demo
        action = wizard_form.save().attach_pickings()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])

        action = self.env['ir.actions.actions']._for_xml_id('stock_picking_batch.stock_add_to_wave_action_stock_picking')
        action['context'] = {'active_model': 'stock.picking', 'active_ids': self.all_pickings.ids}
        self.assertEqual(action.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, action)
        wizard_form.mode = 'existing'
        wizard_form.wave_id = wave
        wizard = wizard_form.save()
        res = wizard.attach_pickings()
        self.assertEqual(set(res['context']['picking_to_wave']), set(self.all_pickings.ids))
        self.assertEqual(res['context']['active_wave_id'], wave.id)

    def test_wave_split_picking(self):
        lines = self.picking_client_1.move_ids.filtered(lambda m: m.product_id == self.productB).move_line_ids
        move = lines.move_id
        self.assertEqual(len(move), 1)
        all_db_pickings = self.env['stock.picking'].search([])
        all_db_pickings.write({'scheduled_date': '2025-01-01 00:00:00'})
        res_dict = lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
        self.assertEqual(res_dict.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertTrue(wave)

        # Original picking lost a stock move
        self.assertTrue(move.picking_id)
        self.assertFalse(move.picking_id == self.picking_client_1)
        self.assertTrue(self.picking_client_1.move_ids)
        self.assertTrue(move.picking_id.batch_id == wave)
        self.assertTrue(lines.batch_id == wave)
        new_all_db_picking = self.env['stock.picking'].search([])
        self.assertEqual(len(all_db_pickings) + 1, len(new_all_db_picking))
        new_picking = new_all_db_picking - all_db_pickings
        self.assertEqual(new_picking.scheduled_date, fields.Datetime.to_datetime('2025-01-01 00:00:00'))

    def test_wave_split_move(self):
        lines = self.picking_internal.move_ids.filtered(lambda m: m.product_id == self.productB).move_line_ids[0:2]
        move = lines.move_id
        all_db_pickings = self.env['stock.picking'].search([])
        res_dict = lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
        self.assertEqual(res_dict.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertTrue(wave)
        self.assertTrue(wave.picking_type_id)

        # Original picking lost a stock move
        self.assertTrue(move.picking_id)
        self.assertTrue(move.picking_id == self.picking_internal)
        self.assertFalse(lines.move_id == move)
        self.assertFalse(move.picking_id.batch_id)
        new_move = lines.move_id
        self.assertTrue(new_move.picking_id.batch_id == wave)
        self.assertTrue(lines.batch_id == wave)
        new_all_db_picking = self.env['stock.picking'].search([])
        self.assertEqual(len(all_db_pickings) + 1, len(new_all_db_picking))

    def test_wave_split_move_uom(self):
        self.uom_dozen = self.env.ref('uom.product_uom_dozen')
        sns = self.env['stock.lot'].create([{
            'name': 'sn-' + str(i),
            'product_id': self.productB.id,
        } for i in range(12)])

        for i in range(12):
            self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 1.0, lot_id=sns[i])
        dozen_move = self.env['stock.move'].create({
            'product_id': self.productB.id,
            'product_uom_qty': 1,
            'product_uom': self.uom_dozen.id,
            'picking_id': self.picking_client_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        dozen_move._action_confirm()
        dozen_move._action_assign()
        self.assertEqual(len(dozen_move.move_line_ids), 12)
        self.assertEqual(dozen_move.move_line_ids.product_uom_id, self.env.ref('uom.product_uom_unit'))

        lines = dozen_move.move_line_ids[0:5]
        res_dict = lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
        self.assertEqual(res_dict.get('res_model'), 'stock.add.to.wave')
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.save().attach_pickings()

        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertFalse(lines.move_id == dozen_move)
        self.assertEqual(lines.batch_id, wave)
        self.assertEqual(dozen_move.product_uom_qty, 0.58)

    def test_wave_mutliple_move_lines(self):
        self.productA = self.env['product.product'].create({
            'name': 'Product Test A',
            'is_storable': True,
        })
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out,
            'company_id': self.env.company.id,
        })
        ml1 = self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'quantity': 5,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'quantity': 5,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        ml2 = self.env['stock.move.line'].create({
            'product_id': self.productA.id,
            'quantity': 5,
            'product_uom_id': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        ml1._add_to_wave()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertFalse(picking.batch_id)
        self.assertEqual(ml1.picking_id.batch_id.id, wave.id)
        self.assertEqual(ml1.picking_id.move_ids.quantity, 5)
        self.assertEqual(ml1.picking_id.move_ids.product_uom_qty, 5)
        self.assertEqual(ml2.picking_id.id, picking.id)
        self.assertEqual(ml2.picking_id.move_ids.quantity, 10)
        self.assertEqual(ml2.picking_id.move_ids.product_uom_qty, 0)

    def test_wave_trigger_errors(self):
        with self.assertRaises(UserError):
            lines = self.picking_client_1.move_line_ids
            res_dict = lines.action_open_add_to_wave()
            wizard_form = Form.from_action(self.env, res_dict)
            wizard_form.mode = 'new'
            wizard = wizard_form.save()
            wizard.attach_pickings()

        with self.assertRaises(UserError):
            self.picking_client_1.company_id = self.env.company
            self.picking_client_2.company_id = self.env['res.company'].create({'name': 'Company 2'})
            lines = (self.picking_client_1 | self.picking_client_2).move_line_ids
            res_dict = lines.action_open_add_to_wave()
            res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
            wizard_form = Form.from_action(self.env, res_dict)
            wizard_form.mode = 'new'
            wizard = wizard_form.save()
            wizard.attach_pickings()

    def test_not_assign_to_wave(self):
        """ Picking
        - Move line A 5 from Container to Cust -> Going to a wave picking
        - Move line A 5 from Container to Cust -> Validate
        ---------------------------------------------
        Create
        - Move A 5 from Container to Cust
        Check it creates a new picking and it's not assign to the wave
        """
        location = self.env['stock.location'].create({
            'name': 'Container',
            'location_id': self.stock_location.id
        })
        self.env['stock.quant']._update_available_quantity(self.productA, location, 5.0, lot_id=self.lots_p_a[0])
        self.env['stock.quant']._update_available_quantity(self.productA, location, 5.0, lot_id=self.lots_p_a[1])
        picking_1 = self.env['stock.picking'].create({
            'location_id': location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out,
            'company_id': self.env.company.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_1.id,
            'picking_type_id': self.picking_type_out,
            'location_id': location.id,
            'location_dest_id': self.customer_location.id,
        })
        picking_1.action_confirm()
        picking_1.action_assign()
        self.assertEqual(len(picking_1.move_line_ids), 2)
        move_line_to_wave = picking_1.move_line_ids[0]
        move_line_to_wave._add_to_wave()
        picking_1.move_line_ids.quantity = 5
        picking_1.move_ids.picked = True
        picking_1._action_done()

        new_move = self.env['stock.move'].create({
            'product_id': self.productA.id,
            'product_uom_qty': 5,
            'product_uom': self.productA.uom_id.id,
            'picking_type_id': self.picking_type_out,
            'location_id': location.id,
            'location_dest_id': self.customer_location.id,
        })
        new_move._action_confirm()
        self.assertTrue(new_move.picking_id)
        self.assertTrue(new_move.picking_id.id not in [picking_1.id, move_line_to_wave.picking_id.id])

    def test_operation_type_in_wave(self):
        """
        Check that the operation type of the picking is set correclty in the wave.
        """
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.reception_steps = 'three_steps'
        self.productA = self.env['product.product'].create({
            'name': 'Product Test A',
            'is_storable': True,
        })
        self.productB = self.env['product.product'].create({
            'name': 'Product Test B',
            'is_storable': True,
        })
        picking = self.env['stock.picking'].create({
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in,
            'company_id': self.env.company.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.customer_location.id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create({
            'product_id': self.productB.id,
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.customer_location.id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        picking.action_confirm()
        picking.move_ids.move_line_ids.write({'quantity': 1})
        picking.move_ids.picked = True
        res_dict = picking.button_validate()
        self.env[res_dict['res_model']].with_context(res_dict['context']).process()

        move_line = self.env["stock.move.line"].search([('product_id', '=', self.productA.id), ('location_id', '=', warehouse.wh_input_stock_loc_id.id)])
        move_line._add_to_wave()
        wave = self.env['stock.picking.batch'].search([
            ('is_wave', '=', True)
        ])
        self.assertEqual(wave.picking_type_id, move_line.picking_type_id)

    def test_validatation_of_partially_empty_picking(self):
        """
            Check that you can validate a wave transfer containing an empty picking,
            that the picking stays unchanged (except for the 'picked' state of the move)
            and is removed from the transfer
        """
        self.productA.tracking = 'none'
        self.productB.tracking = 'none'
        (picking_1, picking_2) = self.env['stock.picking'].create([
            {
            'picking_type_id': self.picking_type_in,
            },
            {
            'picking_type_id': self.picking_type_in,
            },
        ])
        self.env['stock.move'].create([
            {
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': picking_1.location_id.id,
            'location_dest_id': picking_1.location_dest_id.id,
            },
            {
            'product_id': self.productB.id,
            'product_uom_qty': 3,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_2.id,
            'location_id': picking_2.location_id.id,
            'location_dest_id': picking_2.location_dest_id.id,
            },
        ])
        (picking_1 | picking_2).action_confirm()
        wave = self.env['stock.picking.batch'].create({
            'name': 'Wave transfer',
            'picking_ids': [Command.link(picking_1.id), Command.link(picking_2.id)],
            'is_wave': True,
        })
        wave.move_ids.filtered(lambda m: m.product_id == self.productB).quantity = 0.0
        wave.move_ids.picked = True
        wave.action_done()
        self.assertEqual(wave.state, 'done')
        self.assertEqual(wave.picking_ids, picking_1)
        self.assertEqual([picking_1.state, picking_1.move_ids.quantity, picking_1.move_ids.picked], ['done', 2.0, True])
        self.assertEqual([picking_2.state, picking_2.move_ids.quantity, picking_2.move_ids.picked], ['assigned', 0.0, False])

    def test_add_partially_assigned_move_to_batch(self):
        """
            Checks that a picking is linked to the wave transfer in case all of its
            moves are to be linked with the wave transfer.
        """
        picking = self.picking_internal
        # update a move for the moved qty to be less than the initial demand
        picking.move_ids[0].quantity = 10.0
        self.assertRecordValues(picking.move_ids, [{'product_uom_qty': 15.0, 'quantity': 10.0}, {'product_uom_qty': 5.0, 'quantity': 5.0}])
        lines = picking.move_ids.move_line_ids
        res_dict = lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.save().attach_pickings()
        # check that the picking was added to the wave transfer
        wave = picking.batch_id.filtered(lambda b: b.is_wave)
        self.assertTrue(wave)
        # check that the lines are still linked to the original picking
        self.assertEqual(lines.move_id.picking_id, picking)
        # check that no other picking was added to the wave transfer
        self.assertEqual(wave.move_ids, picking.move_ids)

    def test_dont_add_empty_move_to_batch(self):
        """
            Checks that a picking is not linked to the wave transfer in case one
            of its move is not to be linked with the wave transfer.
        """
        picking = self.picking_internal
        move_1, move_2 = picking.move_ids
        # update a move for the moved qty to 0
        move_1.quantity = 0
        self.assertRecordValues(picking.move_ids, [{'product_uom_qty': 15.0, 'quantity': 0.0}, {'product_uom_qty': 5.0, 'quantity': 5.0}])
        lines = picking.move_ids.move_line_ids
        res_dict = lines.action_open_add_to_wave()
        res_dict['context'] = {'active_model': 'stock.move.line', 'active_ids': lines.ids}
        wizard_form = Form.from_action(self.env, res_dict)
        wizard_form.mode = 'new'
        wizard_form.save().attach_pickings()
        # check that a new picking was added to the wave transfer
        new_picking = move_2.picking_id
        self.assertIsNot(picking, new_picking)
        wave = new_picking.batch_id.filtered(lambda b: b.is_wave)
        self.assertTrue(wave)
        self.assertEqual(wave.move_ids, move_2)
        # check that the original picking was not added to a wave transfer
        self.assertFalse(picking.batch_id.filtered(lambda b: b.is_wave))
        self.assertEqual(picking.move_ids, move_1)

    def test_validate_wave_with_zero_qty_picking(self):
        """
            Check that we can validate a wave transfer containing a picking without quantity.
            In that case, the picking remains unchanged and is removed from the wave
        """
        (self.productA | self.productB).tracking = 'none'
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)
        picking_1, picking_2 = self.env['stock.picking'].create([
            {'picking_type_id': self.picking_type_out},
            {'picking_type_id': self.picking_type_out},
        ])
        self.env['stock.move'].create([
            {
            'product_id': self.productA.id,
            'product_uom_qty': 2,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': picking_1.location_id.id,
            'location_dest_id': picking_1.location_dest_id.id,
            },
            {
            'product_id': self.productB.id,
            'product_uom_qty': 3,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_2.id,
            'location_id': picking_2.location_id.id,
            'location_dest_id': picking_2.location_dest_id.id,
            },
        ])
        (picking_1 | picking_2).action_confirm()
        wave = self.env['stock.picking.batch'].create({
            'name': 'Wave transfer',
            'picking_ids': [Command.link(picking_1.id), Command.link(picking_2.id)],
        })
        self.assertEqual((picking_1 | picking_2).mapped('state'), ['assigned', 'assigned'])
        picking_1.move_ids.quantity = 0.0
        wave.action_done()
        self.assertEqual(wave.state, 'done')
        self.assertRecordValues(picking_1.move_ids, [{'state': 'confirmed', 'quantity': 0.0, 'picked': False}])
        self.assertRecordValues(picking_2.move_ids, [{'state': 'done', 'quantity': 3.0, 'picked': True}])
