# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
import odoo.addons.decimal_precision as dp


class BankReconsiliationLine(models.Model):
    _name = 'bank.reconciliation.line'
    _description = 'Reconciliation Line'
    _order = 'date'
    
    date = fields.Date('Date')
    reconcile_id = fields.Many2one('bank.reconciliation', 'Reconcile Record')
    move_id = fields.Many2one('account.move', 'Move')
    document_no = fields.Char('Document No')
    move_line_id = fields.Many2one('account.move.line', 'Move Line Ref')
    rec_date = fields.Date('Reconciliation Date')
    credit = fields.Float('Credit', digits=dp.get_precision('Account'))
    debit = fields.Float('Debit', digits=dp.get_precision('Account'))
    reference = fields.Char(string="Description")
    partner_id = fields.Many2one('res.partner', 'Partner')
    reconciled = fields.Boolean('Reconciled')
    reconciled_done = fields.Boolean('Reconciled', default=False)
    cheque_no = fields.Char('Cheque No')
    state = fields.Selection([
        ('unreconciled', 'Unreconcile'),
        ('reconciled', 'Reconciled'),
    ], string='Status', default="unreconciled")
