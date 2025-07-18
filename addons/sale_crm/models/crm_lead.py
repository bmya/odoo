# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.fields import Domain


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Orders", help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    quotation_count = fields.Integer(compute='_compute_sale_data', string="Number of Quotations")
    sale_order_count = fields.Integer(compute='_compute_sale_data', string="Number of Sale Orders")
    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:
            company_currency = lead.company_currency or self.env.company.currency_id
            sale_orders = lead.order_ids.filtered_domain(self._get_lead_sale_order_domain())
            lead.sale_amount_total = sum(
                order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today()
                )
                for order in sale_orders
            )
            lead.quotation_count = len(lead.order_ids.filtered_domain(self._get_lead_quotation_domain()))
            lead.sale_order_count = len(sale_orders)

    def action_sale_quotations_new(self):
        if not self.partner_id:
            return self.env["ir.actions.actions"]._for_xml_id("sale_crm.crm_quotation_partner_action")
        else:
            return self.action_new_quotation()

    def action_new_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale_crm.sale_action_quotations_new")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_opportunity_id'] = self.id
        return action

    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['domain'] = Domain.AND([[('opportunity_id', '=', self.id)], self._get_action_view_sale_quotation_domain()])
        quotations = self.order_ids.filtered_domain(self._get_action_view_sale_quotation_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def action_view_sale_order(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['context'] = {
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id,
        }
        action['domain'] = Domain.AND([[('opportunity_id', '=', self.id)], self._get_lead_sale_order_domain()])
        orders = self.order_ids.filtered_domain(self._get_lead_sale_order_domain())
        if len(orders) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.id
        return action

    def _get_action_view_sale_quotation_domain(self):
        return [('state', 'in', ('draft', 'sent', 'cancel'))]

    def _get_lead_quotation_domain(self):
        return [('state', 'in', ('draft', 'sent'))]

    def _get_lead_sale_order_domain(self):
        return [('state', 'not in', ('draft', 'sent', 'cancel'))]

    def _prepare_opportunity_quotation_context(self):
        """ Prepares the context for a new quotation (sale.order) by sharing the values of common fields """
        self.ensure_one()
        quotation_context = {
            'default_opportunity_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)]
        }
        if self.team_id:
            quotation_context['default_team_id'] = self.team_id.id
        if self.user_id:
            quotation_context['default_user_id'] = self.user_id.id
        return quotation_context

    def _merge_get_fields_specific(self):
        fields_info = super(CrmLead, self)._merge_get_fields_specific()
        # add all the orders from all lead to merge
        fields_info['order_ids'] = lambda fname, leads: [(4, order.id) for order in leads.order_ids]
        return fields_info

    def _update_revenues_from_so(self, order):
        for opportunity in self:
            if (
                (opportunity.expected_revenue or 0) < order.amount_untaxed
                and order.currency_id == opportunity.company_id.currency_id
            ):
                opportunity.expected_revenue = order.amount_untaxed
                opportunity._track_set_log_message(_('Expected revenue has been updated based on the linked Sales Orders.'))
