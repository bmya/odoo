# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.json import scriptsafe as json_scriptsafe

from odoo import api, fields, models, _

from .base_automation import get_webhook_request_payload


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    name = fields.Char(compute='_compute_name', store=True, readonly=False)

    usage = fields.Selection(selection_add=[
        ('base_automation', 'Automation Rule')
    ], ondelete={'base_automation': 'cascade'})
    base_automation_id = fields.Many2one('base.automation', string='Automation Rule', ondelete='cascade')

    @api.model
    def _warning_depends(self):
        return super()._warning_depends() + [
            'model_id',
            'base_automation_id',
        ]

    def _get_warning_messages(self):
        self.ensure_one()
        warnings = super()._get_warning_messages()

        if self.base_automation_id and self.model_id != self.base_automation_id.model_id:
            warnings.append(
                _("Model of action %(action_name)s should match the one from automated rule %(rule_name)s.",
                    action_name=self.name,
                    rule_name=self.base_automation_id.name
                    )
            )

        return warnings

    @api.depends('usage')
    def _compute_available_model_ids(self):
        """ Stricter model limit: based on automation rule """
        super()._compute_available_model_ids()
        rule_based = self.filtered(lambda action: action.usage == 'base_automation')
        for action in rule_based:
            rule_model = action.base_automation_id.model_id
            action.available_model_ids = rule_model.ids if rule_model in action.available_model_ids else []

    @api.depends('state', 'update_field_id', 'crud_model_id', 'value', 'evaluation_type', 'template_id', 'partner_ids', 'activity_summary', 'sms_template_id', 'webhook_url', 'followers_type', 'followers_partner_field_name')
    def _compute_name(self):
        ''' Only server actions linked to a base_automation get an automatic name. '''
        to_update = self.filtered('base_automation_id')
        for action in to_update:
            match action.state:
                case 'object_write':
                    _field_chain, field_chain_str = action._get_relation_chain("update_path")
                    if action.evaluation_type == 'value':
                        action.name = _("Update %(field_chain_str)s", field_chain_str=field_chain_str)
                    else:
                        action.name = _("Compute %(field_chain_str)s", field_chain_str=field_chain_str)
                case 'object_create':
                    action.name = _(
                    "Create %(model_name)s with name %(value)s",
                        model_name=action.crud_model_id.name,
                        value=action.value
                    )
                case 'webhook':
                    action.name = _("Send Webhook Notification")
                case 'sms':
                    action.name = _(
                    'Send SMS: %(template_name)s',
                    template_name=action.sms_template_id.name
                )
                case 'mail_post':
                    action.name = _(
                        'Send email: %(template_name)s',
                        template_name=action.template_id.name
                    )
                case 'followers':
                    if action.followers_type == 'generic':
                        _field_chain, field_chain_str = action._get_relation_chain("followers_partner_field_name")
                        action.name = _(
                            'Add followers based on field: %(field_chain_str)s',
                            field_chain_str=field_chain_str
                        )
                    else:
                        action.name = _(
                            'Add followers: %(partner_names)s',
                            partner_names=', '.join(action.partner_ids.mapped('name'))
                        )
                case 'remove_followers':
                    if action.followers_type == 'generic':
                        _field_chain, field_chain_str = action._get_relation_chain("followers_partner_field_name")
                        action.name = _(
                            'Remove followers based on field: %(field_chain_str)s',
                            field_chain_str=field_chain_str
                        )
                    else:
                        action.name = _(
                            'Remove followers: %(partner_names)s',
                            partner_names=', '.join(action.partner_ids.mapped('name'))
                        )
                case 'next_activity':
                    action.name = _(
                        'Create activity: %(activity_name)s',
                        activity_name=action.activity_summary or action.activity_type_id.name
                    )
                case other:
                    action.name = dict(action._fields['state']._description_selection(self.env))[action.state]
        # Not sure, but IIRC assignation is mandatory and I don't want the name to be reset by accident
        for action in (self - to_update):
            action.name = action.name or ''

    def _get_eval_context(self, action=None):
        eval_context = super()._get_eval_context(action)
        if action and action.state == "code":
            eval_context['json'] = json_scriptsafe
            payload = get_webhook_request_payload()
            if payload:
                eval_context["payload"] = payload
        return eval_context
