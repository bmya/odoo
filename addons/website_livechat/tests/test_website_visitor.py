# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon
from odoo.tests import new_test_user, tagged
from odoo.exceptions import AccessError


@tagged('website_visitor')
class WebsiteVisitorTestsLivechat(WebsiteVisitorTestsCommon):

    def test_link_to_visitor_livechat(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that conversations
        are merged into main visitor. """
        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])
        all_discuss_channels = (main_visitor + linked_visitor).discuss_channel_ids
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # conversations of both visitors should be merged into main one
        self.assertEqual(len(main_visitor.discuss_channel_ids), 2)
        self.assertEqual(main_visitor.discuss_channel_ids, all_discuss_channels)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        test_partner = self.env['res.partner'].create({'name': 'John Doe'})
        values.update(
            {
                "partner_id": test_partner.id,
                "discuss_channel_ids": [
                    Command.create({"name": "Conversation 1", "livechat_end_dt": fields.Datetime.now()}),
                ],
            }
        )
        return values

    def _prepare_linked_visitor_data(self):
        values = super()._prepare_linked_visitor_data()
        values.update(
            {
                "discuss_channel_ids": [
                    Command.create({"name": "Conversation 2", "livechat_end_dt": fields.Datetime.now()}),
                ],
            }
        )
        return values

    def test_visitor_page_statistics_access(self):
        operator = new_test_user(self.env, "operator", groups="im_livechat.im_livechat_group_user")
        visitor = self._get_last_visitor()
        visitor.with_user(operator).page_count
        with self.assertRaises(AccessError):
            visitor.with_user(operator).page_ids
