# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.bol_shipped_data
import json

from odoo import models, fields

class BolShippedOrderQueueLine(models.Model):
    _name = "bol.shipped.data.queue.line.ept"
    _description = 'BOL Shipped Order Data Queue Line Ept'

    def _get_total_number_of_orders(self):
        for record in self:
            record.total_orders_in_queue_line = len(
                json.loads(record.bol_shipped_data)) if record.bol_shipped_data else 0

    bol_instance_id = fields.Many2one('bol.instance.ept', string='Bol Instance', help="Bol Instance")
    bol_order_id = fields.Char(string='Order Id')
    order_data_id = fields.Char(string='Order Data Id')
    bol_shipped_data = fields.Char('Shipped Data', readonly=True)
    fulfillment_by = fields.Selection([('FBB', 'FBB'), ('FBR', 'FBR')], default='FBR')
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done')], default='draft')
    bol_shipped_order_queue_id = fields.Many2one('bol.shipped.data.queue.ept', string='Shipped Order Data Queue',
                                                 ondelete="cascade")
    sale_order_id = fields.Many2one("sale.order", copy=False,
                                    help="Order created in Odoo.")
    bol_shipped_common_log_lines_ids = fields.One2many("common.log.lines.ept",
                                                       "bol_shipped_order_queue_line_id",
                                                       help="Log lines created against which line.")
    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed", copy=False)
    total_number_of_orders = fields.Integer(readonly=1)
    total_orders_in_queue_line = fields.Integer(compute="_get_total_number_of_orders")
