# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        """We need this method to set Bol Instance in Stock Picking"""
        res = super(StockMove, self)._get_new_picking_values()
        order_id = self.sale_line_id.order_id
        if order_id.bol_order_id:
            res.update({'bol_instance_id': order_id.bol_instance_id.id,
                        'bol_fulfillment_by': order_id.bol_fulfillment_by,
                        'is_bol_delivery_order': True})
        return res
