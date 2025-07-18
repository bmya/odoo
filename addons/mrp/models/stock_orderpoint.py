# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.fields import Domain


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    show_bom = fields.Boolean('Show BoM column', compute='_compute_show_bom')
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Materials', check_company=True,
        domain="[('type', '=', 'normal'), '&', '|', ('company_id', '=', company_id), ('company_id', '=', False), '|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]")
    manufacturing_visibility_days = fields.Float(default=0.0, help="Visibility Days applied on the manufacturing routes.")

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = Domain('orderpoint_id', 'in', self.ids)
        if self.env.context.get('written_after'):
            domain &= Domain('write_date', '>=', self.env.context.get('written_after'))
        production = self.env['mrp.production'].search(domain, limit=1)
        if production:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following replenishment order has been generated'),
                    'message': '%s',
                    'links': [{
                        'label': production.name,
                        'url': f'/odoo/action-mrp.action_mrp_production_form/{production.id}'
                    }],
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        return super()._get_replenishment_order_notification()

    def _compute_allowed_replenishment_uom_ids(self):
        super()._compute_allowed_replenishment_uom_ids()
        for orderpoint in self:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                orderpoint.allowed_replenishment_uom_ids += orderpoint.product_id.bom_ids.product_uom_id

    @api.depends('route_id')
    def _compute_show_bom(self):
        manufacture_route = []
        for res in self.env['stock.rule'].search_read([('action', '=', 'manufacture')], ['route_id']):
            manufacture_route.append(res['route_id'][0])
        for orderpoint in self:
            orderpoint.show_bom = orderpoint.route_id.id in manufacture_route

    def _compute_visibility_days(self):
        res = super()._compute_visibility_days()
        for orderpoint in self:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                orderpoint.visibility_days = orderpoint.manufacturing_visibility_days
        return res

    def _set_visibility_days(self):
        res = super()._set_visibility_days()
        for orderpoint in self:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                orderpoint.manufacturing_visibility_days = orderpoint.visibility_days
        return res

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        # Avoid computing rule_ids in case no manufacture rules.
        if not self.env['stock.rule'].search([('action', '=', 'manufacture')]):
            return res
        # Compute rule_ids only for orderpoint with boms
        orderpoints_with_bom = self.filtered(lambda orderpoint: orderpoint.product_id.variant_bom_ids or orderpoint.product_id.bom_ids)
        for orderpoint in orderpoints_with_bom:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                boms = (orderpoint.product_id.variant_bom_ids or orderpoint.product_id.bom_ids)
                orderpoint.days_to_order = boms and boms[0].days_to_prepare_mo or 0
        return res

    def _quantity_in_progress(self):
        bom_kits = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')
        bom_kit_orderpoints = {
            orderpoint: bom_kits[orderpoint.product_id]
            for orderpoint in self
            if orderpoint.product_id in bom_kits
        }
        orderpoints_without_kit = self - self.env['stock.warehouse.orderpoint'].concat(*bom_kit_orderpoints.keys())
        res = super(StockWarehouseOrderpoint, orderpoints_without_kit)._quantity_in_progress()
        for orderpoint in bom_kit_orderpoints:
            dummy, bom_sub_lines = bom_kit_orderpoints[orderpoint].explode(orderpoint.product_id, 1)
            ratios_qty_available = []
            # total = qty_available + in_progress
            ratios_total = []
            for bom_line, bom_line_data in bom_sub_lines:
                component = bom_line.product_id
                if not component.is_storable or bom_line.product_uom_id.is_zero(bom_line_data['qty']):
                    continue
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, raise_if_failure=False)
                if not qty_per_kit:
                    continue
                qty_by_product_location, dummy = component._get_quantity_in_progress(orderpoint.location_id.ids)
                qty_in_progress = qty_by_product_location.get((component.id, orderpoint.location_id.id), 0.0)
                qty_available = component.qty_available / qty_per_kit
                ratios_qty_available.append(qty_available)
                ratios_total.append(qty_available + (qty_in_progress / qty_per_kit))
            # For a kit, the quantity in progress is :
            #  (the quantity if we have received all in-progress components) - (the quantity using only available components)
            product_qty = min(ratios_total or [0]) - min(ratios_qty_available or [0])
            res[orderpoint.id] = orderpoint.product_id.uom_id._compute_quantity(product_qty, orderpoint.product_uom, round=False)

        bom_manufacture = self.env['mrp.bom']._bom_find(orderpoints_without_kit.product_id, bom_type='normal')
        bom_manufacture = self.env['mrp.bom'].concat(*bom_manufacture.values())
        # add quantities coming from draft MOs
        productions_group = self.env['mrp.production']._read_group(
            [
                ('bom_id', 'in', bom_manufacture.ids),
                ('state', '=', 'draft'),
                ('orderpoint_id', 'in', orderpoints_without_kit.ids),
                ('id', 'not in', self.env.context.get('ignore_mo_ids', [])),
            ],
            ['orderpoint_id', 'product_uom_id'],
            ['product_qty:sum'])
        for orderpoint, uom, product_qty_sum in productions_group:
            res[orderpoint.id] += uom._compute_quantity(
                product_qty_sum, orderpoint.product_uom, round=False)

        # add quantities coming from confirmed MO to be started but not finished
        # by the end of the stock forecast
        in_progress_productions = self.env['mrp.production'].search([
            ('bom_id', 'in', bom_manufacture.ids),
            ('state', '=', 'confirmed'),
            ('orderpoint_id', 'in', orderpoints_without_kit.ids),
            ('id', 'not in', self.env.context.get('ignore_mo_ids', [])),
        ])
        for prod in in_progress_productions:
            date_start, date_finished, orderpoint = prod.date_start, prod.date_finished, prod.orderpoint_id
            lead_days_date = datetime.combine(orderpoint.lead_days_date, time.max)
            if date_start <= lead_days_date < date_finished:
                res[orderpoint.id] += prod.product_uom_id._compute_quantity(
                        prod.product_qty, orderpoint.product_uom, round=False)
        return res

    def _set_default_route_id(self):
        route_ids = self.env['stock.rule'].search([
            ('action', '=', 'manufacture')
        ]).route_id
        for orderpoint in self:
            if not orderpoint.product_id.bom_ids:
                continue
            route_id = orderpoint.rule_ids.route_id & route_ids
            if not route_id:
                continue
            orderpoint.route_id = route_id[0].id
        return super()._set_default_route_id()

    def _prepare_procurement_values(self, date=False, group=False):
        values = super()._prepare_procurement_values(date=date, group=group)
        values['bom_id'] = self.bom_id
        return values

    def _post_process_scheduler(self):
        """ Confirm the productions only after all the orderpoints have run their
        procurement to avoid the new procurement created from the production conflict
        with them. """
        self.env['mrp.production'].sudo().search([
            ('orderpoint_id', 'in', self.ids),
            ('move_raw_ids', '!=', False),
            ('state', '=', 'draft'),
        ]).action_confirm()
        return super()._post_process_scheduler()
