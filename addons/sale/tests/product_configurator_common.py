# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.fields import Command
from odoo.tests import HttpCase
from odoo.tools.misc import file_open

from odoo.addons.uom.tests.common import UomCommon


class TestProductConfiguratorCommon(UomCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup attributes and attributes values
        cls.product_attribute_1 = cls.env['product.attribute'].create({
            'name': 'Legs',
            'sequence': 10,
        })
        product_attribute_value_1 = cls.env['product.attribute.value'].create({
            'name': 'Steel',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 1,
        })
        product_attribute_value_2 = cls.env['product.attribute.value'].create({
            'name': 'Aluminium',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 2,
        })
        product_attribute_2 = cls.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'sequence': 20,
        })
        product_attribute_value_3 = cls.env['product.attribute.value'].create({
            'name': 'White',
            'attribute_id': product_attribute_2.id,
            'html_color': '#FFFFFF',
            'sequence': 1,
        })
        product_attribute_value_4 = cls.env['product.attribute.value'].create({
            'name': 'Black',
            'attribute_id': product_attribute_2.id,
            'html_color': '#000000',
            'sequence': 2,
        })

        # Create product template
        cls.product_product_custo_desk = cls.env['product.template'].create({
            'name': 'Customizable Desk (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.product_attribute_1.id,
                    'value_ids': [Command.link(product_attribute_value_1.id), Command.link(product_attribute_value_2.id)],
                }),
                Command.create({
                    'attribute_id': product_attribute_2.id,
                    'value_ids': [Command.link(product_attribute_value_3.id), Command.link(product_attribute_value_4.id)],
                })
            ]
        })

        # Apply a price_extra for the attribute Aluminium
        cls.product_product_custo_desk.attribute_line_ids[0].product_template_value_ids[1].price_extra = 50.40

        # Add a Custom attribute
        product_attribute_value_custom = cls.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': cls.product_attribute_1.id,
            'sequence': 3,
            'is_custom': True
        })
        cls.product_product_custo_desk.attribute_line_ids[0].write({'value_ids': [(4, product_attribute_value_custom.id)]})

        # Disable the aluminium + black product
        cls.product_product_custo_desk.product_variant_ids[3].active = False

        # Setup a first optional product
        img_path = 'product/static/img/product_product_11-image.jpg'
        img_content = base64.b64encode(file_open(img_path, "rb").read())
        cls.product_product_conf_chair = cls.env['product.template'].create({
            'name': 'Conference Chair (TEST)',
            'image_1920': img_content,
            'list_price': 16.50,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.product_attribute_1.id,
                    'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
                })
            ]
        })

        cls.product_product_conf_chair.attribute_line_ids[0].product_template_value_ids[1].price_extra = 6.40
        cls.product_product_custo_desk.optional_product_ids = [(4, cls.product_product_conf_chair.id)]

        # Setup a second optional product
        cls.product_product_conf_chair_floor_protect = cls.env['product.template'].create({
            'name': 'Chair floor protection (TEST)',
            'list_price': 12.0,
        })
        cls.product_product_conf_chair.optional_product_ids = [(4, cls.product_product_conf_chair_floor_protect.id)]
