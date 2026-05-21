# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestBankReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestBankReconciliation, cls).setUpClass()
        
        # Get standard account types
        cls.liquidity_type = cls.env.ref('account.data_account_type_liquidity')
        cls.revenue_type = cls.env.ref('account.data_account_type_revenue')
        
        # Create a mock Bank GL Account
        cls.bank_account = cls.env['account.account'].create({
            'name': 'Test Bank GL Account',
            'code': '999901',
            'user_type_id': cls.liquidity_type.id,
        })
        
        # Create a counterpart GL Account
        cls.counterpart_account = cls.env['account.account'].create({
            'name': 'Test Counterpart Account',
            'code': '999902',
            'user_type_id': cls.revenue_type.id,
        })
        
        # Create a mock Bank Journal
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Test Bank Journal',
            'code': 'TBNK',
            'type': 'bank',
        })
        cls.bank_journal.default_account_id = cls.bank_account.id
        
        # Create and post some test entries (Move 1 - Debit)
        cls.move_debit = cls.env['account.move'].create({
            'journal_id': cls.bank_journal.id,
            'date': '2026-05-10',
            'line_ids': [
                (0, 0, {
                    'name': 'Test Deposit Line',
                    'account_id': cls.bank_account.id,
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'Deposit Counterpart',
                    'account_id': cls.counterpart_account.id,
                    'debit': 0.0,
                    'credit': 500.0,
                }),
            ]
        })
        cls.move_debit.action_post()

        # Create and post some test entries (Move 2 - Credit)
        cls.move_credit = cls.env['account.move'].create({
            'journal_id': cls.bank_journal.id,
            'date': '2026-05-12',
            'line_ids': [
                (0, 0, {
                    'name': 'Test Payment Line',
                    'account_id': cls.bank_account.id,
                    'debit': 0.0,
                    'credit': 200.0,
                }),
                (0, 0, {
                    'name': 'Payment Counterpart',
                    'account_id': cls.counterpart_account.id,
                    'debit': 200.0,
                    'credit': 0.0,
                }),
            ]
        })
        cls.move_credit.action_post()

    def test_bank_reconciliation_workflow(self):
        # 1. Create a bank reconciliation worksheet
        recon_sheet = self.env['bank.reconciliation'].create({
            'journal_id': self.bank_journal.id,
            'bank_account_id': self.bank_account.id,
            'from_date': '2026-05-01',
            'to_date': '2026-05-20',
            'closing_balance_stmt': 300.0,  # Expected statement balance is 300 (500 debit - 200 credit)
        })
        
        self.assertEqual(recon_sheet.state, 'draft')
        
        # 2. Load the move lines
        recon_sheet.update_record()
        self.assertEqual(len(recon_sheet.reconcileline_ids), 2)
        
        # 3. Verify total debits and credits pulled
        recon_sheet.get_amount()
        self.assertEqual(recon_sheet.debit, 500.0)
        self.assertEqual(recon_sheet.credit, 200.0)
        self.assertEqual(recon_sheet.closing_balance, 300.0)
        
        # 4. Perform select all operation
        recon_sheet.select_all()
        for line in recon_sheet.reconcileline_ids:
            self.assertTrue(line.reconciled)
            
        # 5. Check difference calculation (expected difference should be zero since statement balance is 300)
        recon_sheet.get_amount()
        self.assertEqual(recon_sheet.difference, 0.0)
        
        # 6. Validate the sheet
        recon_sheet.validate()
        self.assertEqual(recon_sheet.state, 'validated')
        
        # 7. Check if linked move lines now store the reconciliation details
        for line in recon_sheet.reconcileline_ids:
            self.assertEqual(line.state, 'reconciled')
            self.assertTrue(line.move_line_id.rec_date)
            self.assertEqual(line.move_line_id.reconcilation_id, recon_sheet.id)
