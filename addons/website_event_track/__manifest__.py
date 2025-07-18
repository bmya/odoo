# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advanced Events',
    'category': 'Marketing',
    'summary': 'Sponsors, Tracks, Agenda, Event News',
    'version': '1.3',
    'depends': ['website_event'],
    'data': [
        'security/ir.model.access.csv',
        'security/event_track_security.xml',
        'data/event_data.xml',
        'data/mail_template_data.xml',
        'data/mail_templates.xml',
        'data/mail_message_subtype_data.xml',
        'data/event_track_data.xml',
        'views/event_templates.xml',
        'views/event_track_templates_agenda.xml',
        'views/event_track_templates_list.xml',
        'views/event_track_templates_reminder.xml',
        'views/event_track_templates_page.xml',
        'views/event_track_templates_proposal.xml',
        'views/event_track_views.xml',
        'views/event_track_location_views.xml',
        'views/event_track_tag_views.xml',
        'views/event_track_stage_views.xml',
        'views/event_track_visitor_views.xml',
        'views/event_event_views.xml',
        'views/event_type_views.xml',
        'views/res_config_settings_view.xml',
        'views/website_visitor_views.xml',
        'views/event_menus.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/event_demo.xml',
        'data/event_track_location_demo.xml',
        'data/event_track_tag_demo.xml',
        'data/event_track_demo.xml',
        'data/event_track_demo_description.xml',
        'data/event_track_visitor_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_event_track/static/src/scss/event_track_templates.scss',
            'website_event_track/static/src/scss/event_track_templates_online.scss',
            'website_event_track/static/src/scss/pwa_frontend.scss',
            'website_event_track/static/lib/idb-keyval/idb-keyval.js',
            'website_event_track/static/src/xml/event_track_proposal_templates.xml',
            'website_event_track/static/src/xml/website_event_pwa.xml',
            'website_event_track/static/src/xml/website_event_track_form_tags_wrapper.xml',
            'website_event_track/static/src/xml/website_event_track_email_reminder.xml',
            'website_event_track/static/src/snippets/**/*.js',
            'website_event_track/static/src/interactions/*',
        ],
        'web.assets_tests': [
            'website_event_track/static/tests/tours/*.js',
        ],
        'website.website_builder_assets': [
            'website_event_track/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
