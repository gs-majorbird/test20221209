# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class CommonLogLineEpt(models.Model):
    _inherit = "common.log.lines.ept"

    bol_order_data_queue_line_id = fields.Many2one("bol.order.data.queue.line.ept", "Bol Order Queue Line")
    bol_shipped_order_queue_line_id = fields.Many2one('bol.shipped.data.queue.line.ept', "Shipped Order Line")

    def bol_create_order_log_line(self, message, model_id, queue_line_id, log_book_id):
        """
        This method used to create a log line.
        @param : self, message, model_id, queue_line_id
        @return: log_line
        @author: Ekta Bhut
        """
        vals = {'message': message,
                'model_id': model_id,
                'res_id': queue_line_id and queue_line_id.id or False,
                'bol_order_data_queue_line_id': queue_line_id and queue_line_id.id or False,
                'bol_shipped_order_queue_line_id': queue_line_id and queue_line_id.id or False,
                'log_book_id': log_book_id.id if log_book_id else False}
        log_line = self.create(vals)
        return log_line
