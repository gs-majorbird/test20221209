# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    is_fbb_warehouse = fields.Boolean("Is FBB Warehouse?")
    bol_unsaleable_location_id = fields.Many2one('stock.location', string='BOL Unsaleable Location')
