# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Jobs',
    'category': 'Website/Website',
    'sequence': 310,
    'version': '1.1',
    'summary': 'Manage your online hiring process',
    'description': "This module allows to publish your available job positions on your website and keep track of application submissions easily.",
    'depends': ['hr_recruitment', 'website_mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_security.xml',
        'data/config_data.xml',
        'views/website_hr_recruitment_templates.xml',
        'views/hr_recruitment_views.xml',
        'views/hr_job_views.xml',
        'views/website_pages_views.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': ['hr_recruitment', 'website_mail'],
    'assets': {
        'web.assets_frontend': [
            'website_hr_recruitment/static/src/scss/**/*',
            'website_hr_recruitment/static/src/interactions/*',
        ],
        'web.assets_backend': [
            'website_hr_recruitment/static/src/js/widgets/copy_link_menuitem.js',
            'website_hr_recruitment/static/src/js/widgets/copy_link_menuitem.xml',
            'website_hr_recruitment/static/src/fields/**/*',
        ],
        'website.website_builder_assets': [
            'website_hr_recruitment/static/src/js/website_hr_recruitment_editor.js',
            'website_hr_recruitment/static/src/website_builder/**/*',
        ],
        'website.assets_editor': [
            'website_hr_recruitment/static/src/js/systray_items/new_content.js',
        ],
        'web.assets_tests': [
            'website_hr_recruitment/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
