# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    move_line_ids_without_package = fields.One2many(
        domain=['&', '|', ('location_dest_id.usage', '!=', 'production'), ('move_id.picking_code', '!=', 'outgoing'),
                     '|', ('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
    display_action_record_components = fields.Selection(
        [('hide', 'Hide'), ('facultative', 'Facultative'), ('mandatory', 'Mandatory')],
        compute='_compute_display_action_record_components')

    @api.depends('state', 'move_ids')
    def _compute_display_action_record_components(self):
        self.display_action_record_components = 'hide'
        for picking in self:
            # Hide if not encoding state or it is not a subcontracting picking
            if picking.state in ('draft', 'cancel', 'done') or not picking._is_subcontract():
                continue
            subcontracted_moves = picking.move_ids.filtered(lambda m: m.is_subcontract)
            if subcontracted_moves._subcontrating_should_be_record():
                picking.display_action_record_components = 'mandatory'
                continue
            if subcontracted_moves._subcontrating_can_be_record():
                picking.display_action_record_components = 'facultative'

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        super()._compute_location_id()

        for picking in self:
            # If this is a subcontractor resupply transfer, set the destination location
            # to the vendor subcontractor location
            subcontracting_resupply_type_id = picking.picking_type_id.warehouse_id.subcontracting_resupply_type_id
            if picking.picking_type_id == subcontracting_resupply_type_id\
                and picking.partner_id.property_stock_subcontractor:
                picking.location_dest_id = picking.partner_id.property_stock_subcontractor


    # -------------------------------------------------------------------------
    # Action methods
    # -------------------------------------------------------------------------
    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for move in self.move_ids:
            if not move.is_subcontract:
                continue
            # Auto set qty_producing/lot_producing_id of MO wasn't recorded
            # manually (if the flexible + record_component or has tracked component)
            productions = move._get_subcontract_production()
            recorded_productions = productions.filtered(lambda p: p._has_been_recorded())
            recorded_qty = sum(recorded_productions.mapped('qty_producing'))
            sm_done_qty = sum(productions._get_subcontract_move().filtered(lambda m: m.picked).mapped('quantity'))
            rounding = self.env['decimal.precision'].precision_get('Product Unit')
            if float_compare(move.product_uom_qty, move.quantity, precision_digits=rounding) > 0 and self.env.context.get('cancel_backorder'):
                move._update_subcontract_order_qty(move.quantity)
            if float_compare(recorded_qty, sm_done_qty, precision_digits=rounding) >= 0:
                continue
            production = productions - recorded_productions
            if not production:
                continue
            if len(production) > 1:
                raise UserError(_("There shouldn't be multiple productions to record for the same subcontracted move."))
            # Manage additional quantities
            quantity_done_move = move.product_uom._compute_quantity(move.quantity, production.product_uom_id)
            if production.product_uom_id.compare(production.product_qty, quantity_done_move) == -1:
                change_qty = self.env['change.production.qty'].create({
                    'mo_id': production.id,
                    'product_qty': quantity_done_move
                })
                change_qty.with_context(skip_activity=True).change_prod_qty()
            # Create backorder MO for each move lines
            amounts = [move_line.quantity for move_line in move.move_line_ids]
            len_amounts = len(amounts)
            productions = production._split_productions({production: amounts}, set_consumed_qty=True)
            productions.move_finished_ids.move_line_ids.write({'quantity': 0})
            for production, move_line in zip(productions, move.move_line_ids):
                if move_line.lot_id:
                    production.lot_producing_id = move_line.lot_id
                production.qty_producing = production.product_qty
                production._set_qty_producing()
            productions[:len_amounts].subcontracting_has_been_recorded = True

        for picking in self:
            productions_to_done = picking._get_subcontract_production()._subcontracting_filter_to_done()
            productions_to_done._subcontract_sanity_check()
            if not productions_to_done:
                continue
            productions_to_done = productions_to_done.sudo()
            production_ids_backorder = []
            if not self.env.context.get('cancel_backorder'):
                production_ids_backorder = productions_to_done.filtered(lambda mo: mo.state == "progress").ids
            productions_to_done.with_context(mo_ids_to_backorder=production_ids_backorder).button_mark_done()
            # For concistency, set the date on production move before the date
            # on picking. (Traceability report + Product Moves menu item)
            minimum_date = min(picking.move_line_ids.mapped('date'))
            production_moves = productions_to_done.move_raw_ids | productions_to_done.move_finished_ids
            production_moves.write({'date': minimum_date - timedelta(seconds=1)})
            production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})

        return res

    def action_record_components(self):
        self.ensure_one()
        move_subcontracted = self.move_ids.filtered(lambda m: m.is_subcontract)
        for move in move_subcontracted:
            production = move._subcontrating_should_be_record()
            if production:
                return move._action_record_components()
        for move in move_subcontracted:
            production = move._subcontrating_can_be_record()
            if production:
                return move._action_record_components()
        raise UserError(_("Nothing to record"))

    # -------------------------------------------------------------------------
    # Subcontract helpers
    # -------------------------------------------------------------------------
    def _is_subcontract(self):
        self.ensure_one()
        return self.picking_type_id.code == 'incoming' and any(m.is_subcontract for m in self.move_ids)

    def _get_subcontract_production(self):
        return self.move_ids._get_subcontract_production()

    def _get_warehouse(self, subcontract_move):
        return subcontract_move.warehouse_id or self.picking_type_id.warehouse_id or subcontract_move.move_dest_ids.picking_type_id.warehouse_id

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        subcontract_move.ensure_one()
        group = self.env['procurement.group'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
        })
        product = subcontract_move.product_id
        warehouse = self._get_warehouse(subcontract_move)
        subcontracting_location = \
            subcontract_move.picking_id.partner_id.with_company(subcontract_move.company_id).property_stock_subcontractor \
            or subcontract_move.company_id.subcontracting_location_id
        vals = {
            'company_id': subcontract_move.company_id.id,
            'procurement_group_id': group.id,
            'subcontractor_id': subcontract_move.picking_id.partner_id.commercial_partner_id.id,
            'picking_ids': [subcontract_move.picking_id.id],
            'product_id': product.id,
            'product_uom_id': subcontract_move.product_uom.id,
            'bom_id': bom.id,
            'location_src_id': subcontracting_location.id,
            'location_dest_id': subcontracting_location.id,
            'product_qty': subcontract_move.product_uom_qty or subcontract_move.quantity,
            'picking_type_id': warehouse.subcontracting_type_id.id,
            'date_start': subcontract_move.date - relativedelta(days=bom.produce_delay),
            'origin': self.name,
        }
        return vals

    def _get_subcontract_mo_confirmation_ctx(self):
        return {}  # To override in mrp_subcontracting_purchase

    def _subcontracted_produce(self, subcontract_details):
        self.ensure_one()
        group_move = defaultdict(list)
        group_by_company = defaultdict(list)
        for move, bom in subcontract_details:
            # do not create extra production for move that have their quantity updated
            if move.move_orig_ids.production_id:
                continue
            quantity = move.product_qty or move.quantity
            if move.product_uom.compare(quantity, 0) <= 0:
                # If a subcontracted amount is decreased, don't create a MO that would be for a negative value.
                continue

            mo_subcontract = self._prepare_subcontract_mo_vals(move, bom)
            # Link the move to the id of the MO's procurement group
            group_move[mo_subcontract['procurement_group_id']] = move
            # Group the MO by company
            group_by_company[move.company_id.id].append(mo_subcontract)

        all_mo = set()
        for company, group in group_by_company.items():
            grouped_mo = self.env['mrp.production'].with_company(company).create(group)
            all_mo.update(grouped_mo.ids)

        all_mo = self.env['mrp.production'].browse(sorted(all_mo))
        all_mo.with_context(self._get_subcontract_mo_confirmation_ctx()).action_confirm()

        for mo in all_mo:
            move = group_move[mo.procurement_group_id.id][0]
            mo.write({'date_finished': move.date})
            finished_move = mo.move_finished_ids.filtered(lambda m: m.product_id == move.product_id)
            finished_move.write({'move_dest_ids': [(4, move.id, False)]})

        all_mo.action_assign()
