# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models

from odoo.tools.misc import file_open


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _inherit = ['image.mixin']
    _description = 'Lunch Product Category'

    @api.model
    def _default_image(self):
        with file_open('lunch/static/img/lunch.png', 'rb') as f:
            return base64.b64encode(f.read())

    name = fields.Char('Product Category', required=True, translate=True)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    product_count = fields.Integer(compute='_compute_product_count', help="The number of products related to this category")
    active = fields.Boolean(string='Active', default=True)
    image_1920 = fields.Image(default=_default_image)

    def _compute_product_count(self):
        product_data = self.env['lunch.product']._read_group([('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        data = {category.id: count for category, count in product_data}
        for category in self:
            category.product_count = data.get(category.id, 0)

    def _sync_active_products(self):
        """ Archiving related lunch product """
        Product = self.env['lunch.product'].with_context(active_test=False)
        all_products = Product.search([('category_id', 'in', self.ids)])
        all_products._sync_active_from_related()

    def action_archive(self):
        super().action_archive()
        self._sync_active_products()

    def action_unarchive(self):
        super().action_unarchive()
        self._sync_active_products()
