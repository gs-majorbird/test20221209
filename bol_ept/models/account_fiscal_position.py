# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_bol_fiscal_position = fields.Boolean()
