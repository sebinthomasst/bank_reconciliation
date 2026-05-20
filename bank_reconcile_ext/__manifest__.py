# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Bank Reconciliation",
    "version": "13.0.1.0.0",
    "category": "Accounting",
    "summary": "Reconcile bank statements with GL account entries",
    "description": "<p>Bank Reconciliation Module allows you to easily reconcile bank statements with GL account entries.</p>",,
    "author": "Sebin Thomas",
    "depends": [
        'account',
        'report_xlsx',
    ],
    "data": [
        'security/ir.model.access.csv',
        'security/user_group.xml',
        'views/bank_reconcilation_view.xml',
        'views/account_move_view.xml',
        'views/sequence.xml',
        'report/report.xml',
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "icon": "static/description/icon.png",
    "license": "AGPL-3",
}