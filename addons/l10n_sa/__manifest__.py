# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['sa'],
    'version': '2.0',
    'author': 'Odoo S.A., DVIT.ME (http://www.dvit.me)',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/saudi_arabia.html',
    'description': """
Saudi Arabia Accounting Module
===========================================================
Saudi Arabia Accounting Basic Charts and Localization

Activates:

- Chart of Accounts
- Taxes
- Vat Filling Report
- Withholding Tax Report
- Fiscal Positions
""",
    'depends': [
        'l10n_gcc_invoice',
        'account',
        'account_debit_note',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_data.xml',
        'data/account_tax_report_data.xml',
        'data/report_paperformat_data.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'wizard/account_debit_note.xml',
        'wizard/account_move_reversal_views.xml',
        'views/report_templates_views.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
