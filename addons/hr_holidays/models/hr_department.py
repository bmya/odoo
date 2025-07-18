# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.fields import Domain

import ast


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    absence_of_today = fields.Integer(
        compute='_compute_leave_count', string='Absence by Today')
    leave_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Time Off to Approve')
    allocation_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Allocation to Approve')

    def _compute_leave_count(self):
        Requests = self.env['hr.leave']
        Allocations = self.env['hr.leave.allocation']
        today_date = datetime.now(timezone.utc).date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))

        leave_data = Requests._read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['department_id'], ['__count'])
        allocation_data = Allocations._read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['department_id'], ['__count'])
        absence_data = Requests._read_group(
            [('department_id', 'in', self.ids), ('state', '=', 'validate'),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start)],
            ['department_id'], ['__count'])

        res_leave = {department.id: count for department, count in leave_data}
        res_allocation = {department.id: count for department, count in allocation_data}
        res_absence = {department.id: count for department, count in absence_data}

        for department in self:
            department.leave_to_approve_count = res_leave.get(department.id, 0)
            department.allocation_to_approve_count = res_allocation.get(department.id, 0)
            department.absence_of_today = res_absence.get(department.id, 0)

    def _get_action_context(self):
        return {
            'search_default_approve': 1,
            'search_default_active_employee': 2,
            'search_default_department_id': self.id,
            'default_department_id': self.id,
            'searchpanel_default_department_id': self.id,
        }

    def action_open_leave_department(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_action_approve_department")
        action['context'] = {
            **self._get_action_context(),
            'search_default_active_time_off': 3,
            'hide_employee_name': 1
        }
        return action

    def action_open_allocation_department(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_allocation_action_approve_department")
        action['context'] = self._get_action_context()
        action['context']['search_default_second_approval'] = 3
        action['domain'] = Domain.AND([ast.literal_eval(action['domain']), [('state', '=', 'confirm')]])
        return action
