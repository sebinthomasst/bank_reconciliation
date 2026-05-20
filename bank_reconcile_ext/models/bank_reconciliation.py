# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Cannot import xlsxwriter.')


class BankReconiliation(models.Model):
    _name = "bank.reconciliation"
    _description = "Bank Statement Reconciliation"
    _order = "name desc"

    name = fields.Char('Bank Reconciliation No', readonly=True, copy=False)
    journal_id = fields.Many2one('account.journal', string="Journal")
    from_date = fields.Date('Date From')
    to_date = fields.Date('Date To')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
    ], string='Status', default="draft")
    bank_account_id = fields.Many2one('account.account', 'Account')
    reconcileline_ids = fields.One2many('bank.reconciliation.line', 'reconcile_id', 'Bank reconciliation line')
    type = fields.Selection([
        ('reconciled', 'Reconciled'),
        ('un_recon', 'To Reconcile'),
        ('all', 'All')
    ], 'Show Only', default='un_recon')
    opening_balance = fields.Float("GL Balance", copy=False, digits=dp.get_precision('Account'))
    opening_balance_stmt = fields.Float("Opening Balance", copy=False, digits=dp.get_precision('Account'))
    closing_balance = fields.Float("GL Closing Balance", copy=False, digits=dp.get_precision('Account'))
    closing_balance_stmt = fields.Float("BNK Balance", copy=False, digits=dp.get_precision('Account'))
    debit = fields.Float("Debit", copy=False, digits=dp.get_precision('Account'))
    credit = fields.Float("Credit", copy=False, digits=dp.get_precision('Account'))
    difference = fields.Float("Difference", copy=False, digits=dp.get_precision('Account'), readonly=False)

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        for record in self:
            if record.journal_id:
                record.bank_account_id = record.journal_id.default_debit_account_id.id
            else:
                record.bank_account_id = False

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Cannot delete records that are already validated.'))
        return super(BankReconiliation, self).unlink()       

    def select_all(self):
        if self.reconcileline_ids:
            for line in self.reconcileline_ids:
                if line.state == 'unreconciled':
                    line.reconciled = True
                if line.reconciled and not line.reconciled_done:
                    if line.debit > 0.00:
                        self.debit -= line.debit
                    elif line.credit > 0.00:
                        self.credit -= line.credit
                    line.reconciled_done = True
            difference_total = self.closing_balance_stmt + self.debit - self.credit     
            self.difference = difference_total - self.closing_balance

    def unselect_all(self):
        if self.reconcileline_ids:
            for line in self.reconcileline_ids:
                if line.state == 'unreconciled' and line.reconciled:
                    line.reconciled = False
                if not line.reconciled and line.reconciled_done:
                    if line.debit > 0.00:
                        self.debit += line.debit
                    elif line.credit > 0.00:
                        self.credit += line.credit
                    line.reconciled_done = False
            difference_total = self.closing_balance_stmt + self.debit - self.credit    
            self.difference = difference_total - self.closing_balance           

    @api.onchange('reconcileline_ids', 'reconcileline_ids.reconciled')
    def onchange_reconciled(self):
        if self.reconcileline_ids:
            for line in self.reconcileline_ids:
                if line.reconciled:
                    if line.debit > 0.00 and not line.reconciled_done:
                        self.debit -= line.debit
                        self.difference -= line.debit
                        line.reconciled_done = True
                    elif line.credit > 0.00 and not line.reconciled_done:
                        self.credit -= line.credit
                        self.difference += line.credit
                        line.reconciled_done = True
                else:
                    if line.debit > 0.00 and line.reconciled_done:
                        self.debit += line.debit
                        self.difference += line.debit
                        line.reconciled_done = False
                    elif line.credit > 0.00 and line.reconciled_done:
                        self.credit += line.credit
                        self.difference -= line.credit
                        line.reconciled_done = False

    @api.depends('reconcileline_ids', 'reconcileline_ids.credit', 'reconcileline_ids.debit', 'bank_account_id')
    def get_amount(self):
        initial_gl_balance = 0.00
        total_debits = 0.00
        total_credits = 0.00
        domain = [('account_id', '=', self.bank_account_id.id), ('date', '<', self.from_date)]
        lines = self.env['account.move.line'].search(domain)
        initial_gl_balance += sum([line.debit - line.credit for line in lines])
        total_debits += sum([drline.debit for drline in self.reconcileline_ids if drline.state == 'unreconciled'])
        total_credits += sum([crline.credit for crline in self.reconcileline_ids if crline.state == 'unreconciled'])
        
        self.opening_balance = initial_gl_balance
        self.closing_balance = initial_gl_balance + total_debits - total_credits
        self.debit = total_debits
        self.credit = total_credits
        balance_total = self.closing_balance_stmt + self.debit - self.credit
        self.difference = balance_total - self.closing_balance

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('bank.reconiliation') or '/'
        return super(BankReconiliation, self).create(vals)

    def validate(self):
        payment_pool = self.env['account.payment'] 
        lines_update = []
        if self.reconcileline_ids:
            reconciled_lines_found = False
            for line in self.reconcileline_ids:
                if line.reconciled and line.state == 'unreconciled':
                    move_line_obj = line.move_line_id
                    line.rec_date = fields.Date.today()
                    lines_update.append((1, line.id, {'state': 'reconciled'}))
                    
                    self.write({
                        'state': 'validated',
                        'reconcileline_ids': lines_update
                    })
                    move_line_obj.write({
                        'rec_date': line.rec_date,
                        'reconcilation_id': self.id
                    })
                    
                    payments = payment_pool.search([('id', '=', move_line_obj.payment_id.id)])
                    if payments:
                        for payment in payments:
                            payment._get_move_reconciled()
                            reconciled_lines_found = True
                            if payment.reconciled_invoice_ids:
                                for invoice in payment.reconciled_invoice_ids:
                                    currencies = invoice._get_lines_onchange_currency().currency_id
                                    currency = len(currencies) == 1 and currencies or invoice.company_id.currency_id
                                    if invoice.type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt') and invoice.state == 'posted' and invoice.invoice_payment_state == 'in_payment':
                                        if currency.is_zero(invoice.amount_residual):
                                            reconciled_payments = invoice._get_reconciled_payments()
                                            if not reconciled_payments or all(rp.is_matched for rp in reconciled_payments):
                                                invoice.invoice_payment_state = 'paid'
                                            else:
                                                invoice.invoice_payment_state = invoice._get_invoice_in_payment_state()
            if not reconciled_lines_found:
                raise UserError(_("No lines have been reconciled."))
        else:
            raise UserError(_("No lines to validate."))
            
        balance_total = self.closing_balance_stmt + self.debit - self.credit
        self.difference = balance_total - self.closing_balance
        return True

    def update_record(self):    
        move_line_pool = self.env['account.move.line'] 
        for record in self:
            lines = []
            if record.bank_account_id:
                for existing_line in record.reconcileline_ids:
                    if existing_line.id:
                        existing_line.unlink()
                
                domain = [('account_id', '=', record.bank_account_id.id)]
                if record.from_date:
                    domain.append(('date', '>=', record.from_date))
                if record.to_date:
                    domain.append(('date', '<=', record.to_date))
                
                move_lines = move_line_pool.search(domain)
                for move_line in move_lines:
                    debit = 0.00
                    credit = 0.00  
                    check_no = ''
                    reconciled = False
                    state = 'unreconciled'
                    payment_name = ''

                    if move_line.payment_id:
                        payment_name = move_line.payment_id.new_name
                        check_no = move_line.payment_id.cheque_no
                    
                    if not payment_name:
                        payment_name = move_line.move_id.name   
                    
                    if move_line.amount_currency:
                        if move_line.amount_currency < 0.00:
                            credit = move_line.amount_currency * -1
                        else:
                            debit = move_line.amount_currency
                        notes = move_line.ref if move_line.ref else move_line.name
                        
                        if move_line.rec_date:
                            reconciled = True  
                            state = 'reconciled'
                    else:
                        debit = move_line.debit or 0.00
                        credit = move_line.credit or 0.00 
                        notes = move_line.ref if move_line.ref else move_line.name
                            
                        if move_line.rec_date:
                            reconciled = True  
                            state = 'reconciled'
                            
                    if state == 'unreconciled':           
                        vals = {
                            'reconcile_id': record.id,
                            'date': move_line.date,
                            'reference': notes,
                            'move_id': move_line.move_id.id,
                            'document_no': payment_name or '',
                            'move_line_id': move_line.id,
                            'partner_id': move_line.partner_id.id or False,
                            'rec_date': move_line.rec_date,
                            'reconciled': reconciled,
                            'state': state,
                            'cheque_no': check_no or False,
                            'debit': move_line.debit,
                            'credit': move_line.credit,
                        }
                        lines.append((0, 0, vals))
                self.write({'reconcileline_ids': lines})
        if self.reconcileline_ids:
            self.get_amount()
        return True     
