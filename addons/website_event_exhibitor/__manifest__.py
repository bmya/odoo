# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Event Exhibitors',
    'category': 'Marketing/Events',
    'sequence': 1004,
    'version': '1.1',
    'summary': 'Event: manage sponsors and exhibitors',
    'website': 'https://www.odoo.com/app/events',
    'depends': [
        'website_event',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/event_sponsor_data.xml',
        'report/website_event_exhibitor_reports.xml',
        'report/website_event_exhibitor_templates.xml',
        'views/event_templates_sponsor.xml',
        'views/event_sponsor_views.xml',
        'views/event_event_views.xml',
        'views/event_exhibitor_templates_list.xml',
        'views/event_exhibitor_templates_page.xml',
        'views/event_type_views.xml',
        'views/event_menus.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/event_demo.xml',
        'data/event_sponsor_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_frontend': [
            'website_event_exhibitor/static/src/scss/event_templates_sponsor.scss',
            'website_event_exhibitor/static/src/scss/event_exhibitor_templates.scss',
            'website_event_exhibitor/static/src/interactions/**/*',
            'website_event_exhibitor/static/src/components/exhibitor_connect_closed_dialog/**/*',
        ],
        'web.report_assets_common': [
            '/website_event_exhibitor/static/src/scss/event_full_page_ticket_report.scss',
        ],
        'website.website_builder_assets': [
            'website_event_exhibitor/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
