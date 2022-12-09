# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    bol_order_item_id = fields.Char("Bol Order item line")
