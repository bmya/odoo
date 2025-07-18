# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    hours_last_month = fields.Float(related='employee_id.hours_last_month')
    hours_last_month_display = fields.Char(related='employee_id.hours_last_month_display')
    attendance_state = fields.Selection(related='employee_id.attendance_state')
    last_check_in = fields.Datetime(related='employee_id.last_attendance_id.check_in')
    last_check_out = fields.Datetime(related='employee_id.last_attendance_id.check_out')
    total_overtime = fields.Float(related='employee_id.total_overtime')
    attendance_manager_id = fields.Many2one(related='employee_id.attendance_manager_id', readonly=False)
    display_extra_hours = fields.Boolean(related='company_id.hr_attendance_display_overtime')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'hours_last_month',
            'hours_last_month_display',
            'attendance_state',
            'last_check_in',
            'last_check_out',
            'total_overtime',
            'attendance_manager_id',
            'display_extra_hours',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'attendance_manager_id',
        ]

    def _clean_attendance_officers(self):
        attendance_officers = self.env['hr.employee'].search(
            [('attendance_manager_id', 'in', self.ids)]).attendance_manager_id
        officers_to_remove_ids = self - attendance_officers
        if officers_to_remove_ids:
            self.env.ref('hr_attendance.group_hr_attendance_officer').user_ids = [(3, user.id) for user in
                                                                               officers_to_remove_ids]

    @api.model
    def get_overtime_data(self, domain=None, employee_id=None):
        domain = [] if domain is None else domain
        validated_overtime = {
            overtime[0].id: overtime[1]
            for overtime in self.env["hr.attendance.overtime"]._read_group(
                domain=domain + [('adjustment', '=', False)],
                groupby=['employee_id'],
                aggregates=['duration:sum']
            )
        }
        overtime_adjustments = {
            overtime[0].id: overtime[1]
            for overtime in self.env["hr.attendance.overtime"]._read_group(
                domain=domain + [('adjustment', '=', True)],
                groupby=['employee_id'],
                aggregates=['duration:sum']
            )
        }
        return {"validated_overtime": validated_overtime, "overtime_adjustments": overtime_adjustments}

    def action_open_last_month_attendances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendances This Month"),
            "res_model": "hr.attendance",
            "views": [[self.env.ref('hr_attendance.hr_attendance_employee_simple_tree_view').id, "list"]],
            "context": {
                "create": 0,
                "search_default_check_in_filter": 1,
            },
            "domain": [('employee_id', '=', self.employee_id.id)]
        }

    def action_open_total_overtime(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Overtime"),
            "res_model": "hr.attendance.overtime",
            "views": [[False, "list"]],
            "context": {
                "create": 0,
                'employee_id': self.employee_id.id,
                'model': 'res.users',
            },
            "domain": [('employee_id', '=', self.employee_id.id)]
        }
