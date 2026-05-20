# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    rec_date = fields.Date('Reconciled Date')
    reconcilation_id = fields.Many2one('bank.reconciliation', 'Reconciled Record')
