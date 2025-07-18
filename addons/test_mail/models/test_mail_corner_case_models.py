# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MailPerformanceThread(models.Model):
    _name = 'mail.performance.thread'
    _description = 'Performance: mail.thread'
    _inherit = ['mail.thread']

    name = fields.Char()
    value = fields.Integer()
    value_pc = fields.Float(compute="_value_pc", store=True)
    track = fields.Char(default='test', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100


class MailPerformanceThreadRecipients(models.Model):
    _name = 'mail.performance.thread.recipients'
    _description = 'Performance: mail.thread, for recipients'
    _inherit = ['mail.thread']
    _primary_email = 'email_from'

    name = fields.Char()
    value = fields.Integer()
    email_from = fields.Char('Email From')
    partner_id = fields.Many2one('res.partner', string='Customer')
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)


class MailPerformanceTracking(models.Model):
    _name = 'mail.performance.tracking'
    _description = 'Performance: multi tracking'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    field_0 = fields.Char(tracking=True)
    field_1 = fields.Char(tracking=True)
    field_2 = fields.Char(tracking=True)


class MailTestFieldType(models.Model):
    """ Test default values, notably type, messing through models during gateway
    processing (i.e. lead.type versus attachment.type). """
    _description = 'Test Field Type'
    _name = "mail.test.field.type"
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    datetime = fields.Datetime(default=fields.Datetime.now)
    customer_id = fields.Many2one('res.partner', 'Customer')
    type = fields.Selection([('first', 'First'), ('second', 'Second')])
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Emulate an addon that alters the creation context, such as `crm`
        if not self.env.context.get('default_type'):
            self = self.with_context(default_type='first')
        return super(MailTestFieldType, self).create(vals_list)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailTestLang(models.Model):
    """ A simple chatter model with lang-based capabilities, allowing to
    test translations. """
    _description = 'Lang Chatter Model'
    _name = "mail.test.lang"
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    customer_id = fields.Many2one('res.partner')
    lang = fields.Char('Lang')

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        for group in [g for g in groups if g[0] in('follower', 'customer')]:
            group_options = group[2]
            group_options['has_button_access'] = True
        return groups

# ------------------------------------------------------------
# TRACKING MODELS
# ------------------------------------------------------------


class MailTestTrackAllM2m(models.Model):
    _description = 'Sub-model: pseudo tags for tracking'
    _name = "mail.test.track.all.m2m"
    _inherit = ['mail.thread']

    name = fields.Char('Name')


class MailTestTrackAllO2m(models.Model):
    _description = 'Sub-model: pseudo tags for tracking'
    _name = "mail.test.track.all.o2m"
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    mail_track_all_id = fields.Many2one('mail.test.track.all')


class MailTestTrackAllPropertiesParent(models.Model):
    _description = 'Properties Parent'
    _name = "mail.test.track.all.properties.parent"

    definition_properties = fields.PropertiesDefinition()


class MailTestTrackAll(models.Model):
    _description = 'Test tracking on all field types'
    _name = "mail.test.track.all"
    _inherit = ['mail.thread']

    boolean_field = fields.Boolean('Boolean', tracking=1)
    char_field = fields.Char('Char', tracking=2)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    date_field = fields.Date('Date', tracking=3)
    datetime_field = fields.Datetime('Datetime', tracking=4)
    float_field = fields.Float('Float', tracking=5)
    float_field_with_digits = fields.Float('Precise Float', digits=(10, 8), tracking=5)
    html_field = fields.Html('Html', tracking=False)
    integer_field = fields.Integer('Integer', tracking=7)
    many2many_field = fields.Many2many(
        'mail.test.track.all.m2m', string='Many2Many',
        tracking=8)
    many2one_field_id = fields.Many2one('res.partner', string='Many2one', tracking=9)
    monetary_field = fields.Monetary('Monetary', tracking=10)
    one2many_field = fields.One2many(
        'mail.test.track.all.o2m', 'mail_track_all_id',
        string='One2Many',
        tracking=11)
    properties_parent_id = fields.Many2one('mail.test.track.all.properties.parent', tracking=True)
    properties = fields.Properties('Properties', definition='properties_parent_id.definition_properties')
    selection_field = fields.Selection(
        string='Selection',
        selection=[('first', 'FIRST'), ('second', 'SECOND')],
        tracking=12)
    text_field = fields.Text('Text', tracking=13)

    name = fields.Char('Name')


class MailTestTrackCompute(models.Model):
    _description = "Test tracking with computed fields"
    _name = "mail.test.track.compute"
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', tracking=True)
    partner_name = fields.Char(related='partner_id.name', store=True, tracking=True)
    partner_email = fields.Char(related='partner_id.email', store=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', tracking=True)


class MailTestTrackDurationMixin(models.Model):
    _description = 'Fake model to test the mixin mail.tracking.duration.mixin'
    _name = "mail.test.track.duration.mixin"
    _track_duration_field = 'customer_id'
    _inherit = ['mail.thread', 'mail.tracking.duration.mixin']

    name = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailTestTrackGroups(models.Model):
    _description = "Test tracking with groups"
    _name = "mail.test.track.groups"
    _inherit = ['mail.thread']

    name = fields.Char(tracking=1)
    partner_id = fields.Many2one('res.partner', tracking=2, groups="base.group_user")
    secret = fields.Char(tracking=3, groups="base.group_user")


class MailTestTrackMonetary(models.Model):
    _description = 'Test tracking monetary field'
    _name = "mail.test.track.monetary"
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company')
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True, tracking=True)
    revenue = fields.Monetary('Revenue', currency_field='company_currency', tracking=True)


class MailTestTrackSelection(models.Model):
    """ Test tracking for selection fields """
    _description = 'Test Selection Tracking'
    _name = "mail.test.track.selection"
    _inherit = ['mail.thread']

    name = fields.Char()
    selection_type = fields.Selection([('first', 'First'), ('second', 'Second')], tracking=True)


# ------------------------------------------------------------
# OTHER
# ------------------------------------------------------------


class MailTestMultiCompany(models.Model):
    """ This model can be used in multi company tests, with attachments support
    for checking record update in MC """
    _description = "Test Multi Company Mail"
    _name = "mail.test.multi.company"
    _inherit = ['mail.thread.main.attachment']

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class MailTestMultiCompanyRead(models.Model):
    """ Just mail.test.simple, but multi company and supporting posting
    even if the user has no write access. """
    _description = 'Simple Chatter Model'
    _name = "mail.test.multi.company.read"
    _inherit = ['mail.test.multi.company']
    _mail_post_access = 'read'


class MailTestMultiCompanyWithActivity(models.Model):
    """ This model can be used in multi company tests with activity"""
    _description = "Test Multi Company Mail With Activity"
    _name = "mail.test.multi.company.with.activity"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char()
    company_id = fields.Many2one("res.company")


class MailTestNothread(models.Model):
    """ Models not inheriting from mail.thread but using some cross models
    capabilities of mail. """
    _description = "NoThread Model"
    _name = "mail.test.nothread"

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    customer_id = fields.Many2one('res.partner')

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']
