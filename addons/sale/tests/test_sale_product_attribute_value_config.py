# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.test_product_attribute_value_config import (
    TestProductAttributeValueCommon,
)


@tagged('post_install', '-at_install')
class TestSaleProductAttributeValueConfig(TestProductAttributeValueCommon):

    def test_01_is_combination_possible_archived(self):
        """The goal is to test the possibility of archived combinations.

        This test could not be put into product module because there was no
        model which had product_id as required and without cascade on delete.
        Here we have the sales order line in this situation.

        This is a necessary condition for `_create_variant_ids` to archive
        instead of delete the variants.
        """
        def do_test(self):
            computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
            computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            variant = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)
            variant2 = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_2)

            self.assertTrue(variant)
            self.assertTrue(variant2)

            # Create a dummy SO to prevent the variant from being deleted by
            # _create_variant_ids() because the variant is a related field that
            # is required on the SO line
            so = self.env['sale.order'].create({'partner_id': 1})
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant.id
            })
            # additional variant to test correct ignoring when mismatch values
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant2.id
            })

            variant2.active = False
            # CASE: 1 not archived, 2 archived
            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_2))
            # CASE: both archived combination (without no_variant)
            variant.active = False
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_2))
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: OK after attribute line removed
            self.computer_hdd_attribute_lines.write({'active': False})
            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8))

            # CASE: not archived (with no_variant)
            self.hdd_attribute.create_variant = 'no_variant'
            self._add_hdd_attribute_line()
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: archived combination found (with no_variant)
            variant = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)
            variant.active = False
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: archived combination has different attributes (including no_variant)
            self.computer_ssd_attribute_lines.write({'active': False})

            variant4 = self.computer._get_variant_for_combination(computer_ram_8 + computer_hdd_1)
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant4.id
            })
            self.assertTrue(self.computer._is_combination_possible(computer_ram_8 + computer_hdd_1))

            # CASE: archived combination has different attributes (without no_variant)
            self.computer_hdd_attribute_lines.write({'active': False})
            self.hdd_attribute.create_variant = 'always'
            self._add_hdd_attribute_line()
            computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
            computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            variant5 = self.computer._get_variant_for_combination(computer_ram_8 + computer_hdd_1)
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant5.id
            })

            self.assertTrue(variant4 != variant5)

            self.assertTrue(self.computer._is_combination_possible(computer_ram_8 + computer_hdd_1))

        computer_ssd_256_before = self._get_product_template_attribute_value(self.ssd_256)

        do_test(self)

        # CASE: add back the removed attribute and try everything again
        self.computer_ssd_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.ssd_attribute.id,
            'value_ids': [(6, 0, [self.ssd_256.id, self.ssd_512.id])],
        })

        computer_ssd_256_after = self._get_product_template_attribute_value(self.ssd_256)
        self.assertEqual(computer_ssd_256_after, computer_ssd_256_before)
        self.assertEqual(computer_ssd_256_after.attribute_line_id, computer_ssd_256_before.attribute_line_id)
        do_test(self)
