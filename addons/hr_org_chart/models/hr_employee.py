# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    subordinate_ids = fields.One2many('hr.employee', string='Subordinates', compute='_compute_subordinates', help="Direct and indirect subordinates",
                                      compute_sudo=True)
    is_subordinate = fields.Boolean(compute="_compute_is_subordinate", search="_search_is_subordinate")


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    subordinate_ids = fields.One2many(related='employee_id.subordinate_ids', compute_sudo=True)
    is_subordinate = fields.Boolean(related='employee_id.is_subordinate')
