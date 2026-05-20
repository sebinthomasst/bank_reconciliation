# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = "Account Move Extension"
            
    def _get_invoice_in_payment_state(self):
        """ Hook to specify the state when the invoice becomes fully paid.
        Enforces standard 'paid' state instead of default 'in_payment' state.
        """
        return 'paid'