# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import json

from odoo import models, fields

class BolOrderQueueLineEpt(models.Model):
    _name = 'bol.order.data.queue.line.ept'
    _description = "Bol Order Data Queue Line"
    _rec_name = "bol_order_data_queue_id"

    def _get_total_number_of_orders(self):
        for record in self:
            record.total_orders_in_queue_line = len(json.loads(record.bol_order_data)) if record.bol_order_data else 0

    bol_order_data_queue_id = fields.Many2one('bol.queue.ept', ondelete="cascade")
    bol_order_id = fields.Char('Order Id', readonly=True, required=True, copy=False, default="New")
    bol_order_data = fields.Char('Order Data', readonly=True)
    bol_instance_id = fields.Many2one('bol.instance.ept', string='Instance',
                                      help="Order imported from this Bol Instance.")
    sale_order_id = fields.Many2one("sale.order", copy=False,
                                    help="Order created in Odoo.")
    state = fields.Selection([('done', 'Done'),
                              ('failed', 'Failed'),
                              ('draft', 'Draft'),
                              ('cancel', 'Cancel')],
                             default='draft')
    bol_order_common_log_lines_ids = fields.One2many("common.log.lines.ept",
                                                     "bol_order_data_queue_line_id",
                                                     help="Log lines created against which line.")
    processed_at = fields.Datetime(help="Shows Date and Time, When the data is processed",
                                   copy=False)
    total_number_of_orders = fields.Integer(readonly=1)
    total_orders_in_queue_line = fields.Integer(compute="_get_total_number_of_orders")
