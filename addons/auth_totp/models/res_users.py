# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import logging
import os
import re

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools import sql

from odoo.addons.auth_totp.models.totp import TOTP, TOTP_SECRET_SIZE

_logger = logging.getLogger(__name__)

compress = functools.partial(re.sub, r'\s', '')

TOTP_RATE_LIMITS = {
    'send_email': (5, 3600),
    'code_check': (5, 3600),
}


class ResUsers(models.Model):
    _inherit = 'res.users'

    totp_secret = fields.Char(copy=False, groups=fields.NO_ACCESS, compute='_compute_totp_secret', inverse='_inverse_token')
    totp_last_counter = fields.Integer(copy=False, groups=fields.NO_ACCESS)
    totp_enabled = fields.Boolean(string="Two-factor authentication", compute='_compute_totp_enabled', search='_totp_enable_search')
    totp_trusted_device_ids = fields.One2many('auth_totp.device', 'user_id', string="Trusted Devices")

    def init(self):
        super().init()
        if not sql.column_exists(self.env.cr, self._table, "totp_secret"):
            self.env.cr.execute("ALTER TABLE res_users ADD COLUMN totp_secret varchar")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['totp_enabled', 'totp_trusted_device_ids']

    def _mfa_type(self):
        r = super()._mfa_type()
        if r is not None:
            return r
        if self.totp_enabled:
            return 'totp'

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self._mfa_type() == 'totp':
            return '/web/login/totp'

    @api.depends('totp_secret')
    def _compute_totp_enabled(self):
        for r, v in zip(self, self.sudo()):
            r.totp_enabled = bool(v.totp_secret)

    def _rpc_api_keys_only(self):
        # 2FA enabled means we can't allow password-based RPC
        self.ensure_one()
        return self.totp_enabled or super()._rpc_api_keys_only()

    def _get_session_token_fields(self):
        return super()._get_session_token_fields() | {'totp_secret'}

    def _check_credentials(self, credentials, env):
        if credentials['type'] == 'totp':
            self._totp_rate_limit('code_check')
            sudo = self.sudo()
            key = base64.b32decode(sudo.totp_secret)
            match = TOTP(key).match(credentials['token'])
            if match is None:
                _logger.info("2FA check: FAIL for %s %r", self, sudo.login)
                raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))

            if sudo.totp_last_counter and match <= sudo.totp_last_counter:
                _logger.warning("2FA check: REUSE for %s %r", self, sudo.login)
                raise AccessDenied(_("Verification failed, please use the latest 6-digit code"))

            sudo.totp_last_counter = match
            _logger.info("2FA check: SUCCESS for %s %r", self, sudo.login)
            self._totp_rate_limit_purge('code_check')
            return {
                'uid': self.env.user.id,
                'auth_method': 'totp',
                'mfa': 'default',
            }
        return super()._check_credentials(credentials, env)

    def _totp_try_setting(self, secret, code):
        if self.totp_enabled or self != self.env.user:
            _logger.info("2FA enable: REJECT for %s %r", self, self.login)
            return False

        secret = compress(secret).upper()
        match = TOTP(base64.b32decode(secret)).match(code)
        if match is None:
            _logger.info("2FA enable: REJECT CODE for %s %r", self, self.login)
            return False

        self.sudo().totp_secret = secret
        self.sudo().totp_last_counter = match
        if request:
            self.env.flush_all()
            # update session token so the user does not get logged out (cache cleared by change)
            new_token = self.env.user._compute_session_token(request.session.sid)
            request.session.session_token = new_token

        _logger.info("2FA enable: SUCCESS for %s %r", self, self.login)
        return True

    def _totp_rate_limit(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        limit, interval = TOTP_RATE_LIMITS[limit_type]
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        ip = request.httprequest.environ['REMOTE_ADDR']
        domain = [
            ('user_id', '=', self.id),
            ('create_date', '>=', datetime.now() - timedelta(seconds=interval)),
            ('limit_type', '=', limit_type),
        ]
        count = RateLimitLog.search_count(domain)
        if count >= limit:
            descriptions = {
                'send_email': _('You reached the limit of authentication mails sent for your account, please try again later.'),
                'code_check': _('You reached the limit of code verifications for your account, please try again later.'),
            }
            description = descriptions[limit_type]
            raise AccessDenied(description)
        RateLimitLog.create({
            'user_id': self.id,
            'ip': ip,
            'limit_type': limit_type,
        })

    def _totp_rate_limit_purge(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        RateLimitLog.search([
            ('user_id', '=', self.id),
            ('limit_type', '=', limit_type),
        ]).unlink()

    @check_identity
    def action_totp_disable(self):
        logins = ', '.join(map(repr, self.mapped('login')))
        if not (self == self.env.user or self.env.user._is_admin() or self.env.su):
            _logger.info("2FA disable: REJECT for %s (%s) by uid #%s", self, logins, self.env.user.id)
            return False

        self.revoke_all_devices()
        self.sudo().write({'totp_secret': False})

        if request and self == self.env.user:
            self.env.flush_all()
            # update session token so the user does not get logged out (cache cleared by change)
            new_token = self.env.user._compute_session_token(request.session.sid)
            request.session.session_token = new_token

        _logger.info("2FA disable: SUCCESS for %s (%s) by uid #%s", self, logins, self.env.user.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'message': _("Two-factor authentication disabled for the following user(s): %s", ', '.join(self.mapped('name'))),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @check_identity
    def action_totp_enable_wizard(self):
        if self.env.user != self:
            raise UserError(_("Two-factor authentication can only be enabled for yourself"))

        if self.totp_enabled:
            raise UserError(_("Two-factor authentication already enabled"))

        secret_bytes_count = TOTP_SECRET_SIZE // 8
        secret = base64.b32encode(os.urandom(secret_bytes_count)).decode()
        # format secret in groups of 4 characters for readability
        secret = ' '.join(map(''.join, zip(*[iter(secret)]*4)))
        w = self.env['auth_totp.wizard'].create({
            'user_id': self.id,
            'secret': secret,
        })
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'auth_totp.wizard',
            'name': _("Two-Factor Authentication Activation"),
            'res_id': w.id,
            'views': [(False, 'form')],
            'context': self.env.context | {'dialog_size': 'medium'},
        }

    @check_identity
    def revoke_all_devices(self):
        self._revoke_all_devices()

    def _revoke_all_devices(self):
        self.totp_trusted_device_ids._remove()

    @api.model
    def change_password(self, old_passwd, new_passwd):
        self.env.user._revoke_all_devices()
        return super().change_password(old_passwd, new_passwd)

    def _compute_totp_secret(self):
        for user in self:
            if not user.id:
                user.totp_secret = user._origin.totp_secret
                continue
            self.env.cr.execute('SELECT totp_secret FROM res_users WHERE id=%s', (user.id,))
            user.totp_secret = self.env.cr.fetchone()[0]

    def _inverse_token(self):
        self.sudo().totp_last_counter = False
        for user in self:
            secret = user.totp_secret if user.totp_secret else None
            self.env.cr.execute('UPDATE res_users SET totp_secret = %s WHERE id=%s', (secret, user.id))

    def _totp_enable_search(self, operator, value):
        value = not value if operator == '!=' else value
        if value:
            self.env.cr.execute("SELECT id FROM res_users WHERE totp_secret IS NOT NULL")
        else:
            self.env.cr.execute("SELECT id FROM res_users WHERE totp_secret IS NULL OR totp_secret='false'")
        result = self.env.cr.fetchall()
        return [('id', 'in', [x[0] for x in result])]
