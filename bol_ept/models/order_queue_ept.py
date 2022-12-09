# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import logging
import time

from odoo import models, fields, api

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class BolOrderQueueEpt(models.Model):
    _name = 'bol.queue.ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Bol Order Queue"
    _order = "create_date desc"

    name = fields.Char('Queue Reference', readonly=True, required=True, copy=False, default="New")
    bol_instance_id = fields.Many2one('bol.instance.ept', string="Instance")
    import_time = fields.Datetime('Imported at', default=lambda self: fields.Datetime.now())
    state = fields.Selection([('draft', 'Draft'),
                              ('partial', 'Partically Completed'),
                              ('done', 'Done'),
                              ('failed', 'Failed')], default='draft')
    fulfilment_by = fields.Selection([('FBB', 'FBB'), ('FBR', 'FBR')], 'Fulfilment Method',
                                     readonly=True)

    order_data_queue_line_ids = fields.One2many("bol.order.data.queue.line.ept",
                                                "bol_order_data_queue_id")
    order_queue_line_total_record = fields.Integer(string='Total Records',
                                                   compute='_compute_order_queue_line_record')
    order_queue_line_draft_record = fields.Integer(string='Draft Records',
                                                   compute='_compute_order_queue_line_record')
    order_queue_line_fail_record = fields.Integer(string='Fail Records',
                                                  compute='_compute_order_queue_line_record')
    order_queue_line_done_record = fields.Integer(string='Done Records',
                                                  compute='_compute_order_queue_line_record')
    order_queue_line_cancel_record = fields.Integer(string='Cancel Records',
                                                    compute='_compute_order_queue_line_record')
    bol_order_common_log_book_id = fields.Many2one("common.log.book.ept",
                                                   help="""Related Log book which has all logs for current queue.""")

    bol_order_common_log_lines_ids = fields.One2many('common.log.lines.ept',
                                                     compute="_compute_order_queue_log_lines")

    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False,
                                       help="it is used  to find the action require queue")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    log_count = fields.Integer(compute="get_log_count", string="Order Log Counter",
                               help="Count number of created order logs", store=False)

    def _compute_order_queue_log_lines(self):
        """
        List Bol Orders Queue Log lines
        :return: Queue log line
        @author: Ekta bhut, 18th March 2021
        """
        for queue in self:
            log_book_obj = self.env['common.log.book.ept']
            model_id = self.env['ir.model']._get('bol.queue.ept').id
            domain = [('res_id', '=', queue.id), ('model_id', '=', model_id)]
            log_book_id = log_book_obj.search(domain)
            queue.bol_order_common_log_lines_ids = log_book_id and log_book_id[
                0].log_lines.ids or False

    def get_log_count(self):
        """
        Log count related queue job.
        :return: Log count
        @author: Ekta Bhut, 18th March 2021
        """
        model_id = self.env['ir.model']._get('bol.queue.ept').id
        log_obj = self.env['common.log.book.ept']
        self.log_count = log_obj.search_count([('res_id', '=', self.id), ('model_id', '=', model_id)])

    def list_of_process_logs(self):
        """
        This Method relocate mismatch log.
        @author: Ekta Bhut, 18th March 2021
        """
        bol_job_log_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.queue.ept').id
        records = bol_job_log_obj.search( \
                [('model_id', '=', model_id),
                 ('res_id', '=', self.id)])
        action = {
            'domain': "[('id', 'in', " + str(records.ids) + " )]",
            'name': 'Mismatch Logs',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'common.log.book.ept',
            'type': 'ir.actions.act_window',
        }
        return action

    @api.depends('order_data_queue_line_ids.state')
    def _compute_order_queue_line_record(self):
        """This is used for count of total records of order queue lines.
            @param : self
            @author: Ekta Bhut, 18th March 2021
        """
        for order_queue in self:
            queue_lines = order_queue.order_data_queue_line_ids
            order_queue.order_queue_line_total_record = len(queue_lines)
            order_queue.order_queue_line_draft_record = len(queue_lines.filtered(lambda x: x.state == "draft"))
            order_queue.order_queue_line_done_record = len(queue_lines.filtered(lambda x: x.state == "done"))
            order_queue.order_queue_line_fail_record = len(queue_lines.filtered(lambda x: x.state == "failed"))
            order_queue.order_queue_line_cancel_record = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.model
    def create(self, vals):
        """
        We generate the name of the queue in sequencial manner.
        :param vals: values provided to create a record
        :return: Newly created record with a newly generated sequence
        @author: Ekta Bhut, 18th March 2021
        """
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('bol.order.data.queue') or 'New'
        result = super(BolOrderQueueEpt, self).create(vals)
        return result

    def import_order_queue(self, instance, fulfillment_by):
        """
        Create queue for open order
        :param instance: Bol Instance
        :param fulfillment_by: FBR & FBB
        :return: True
        """
        log_book_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.queue.ept').id
        message = "Import %s open orders for Bol instance : %s" % (fulfillment_by, instance.name)
        log_rec = log_book_obj.bol_create_common_log_book('import', instance, model_id,
                                                          message, self.id)
        order_queue_list = self.create_queue_for_open_orders(instance, fulfillment_by, log_rec)
        return order_queue_list

    def create_queue_for_open_orders(self, instance, fulfilment_by, log_rec):
        """
        This method is used for Create queue for Open orders
        :param instance: Bol Instance
        :param fulfilment_by: 'FBB' or 'FBR'
        :param log_rec: Common Log book record
        :return:
        @author : Ekta Bhut
        """
        transaction_log_obj = self.env['common.log.lines.ept']
        bol_order_queue_line_obj = self.env['bol.order.data.queue.line.ept']
        order_queue_id = self.env['bol.queue.ept'].create({'bol_instance_id': instance.id,
                                                           'fulfilment_by': fulfilment_by})
        order_queue_list = [order_queue_id.id]
        page = 0
        counter = 0
        try:
            while True:
                counter += 1
                if counter == 11:
                    order_queue_id = self.env['bol.queue.ept'].create({'bol_instance_id': instance.id,
                                                                       'fulfilment_by': fulfilment_by})
                    order_queue_list.append(order_queue_id.id)
                    counter = 0
                    self._cr.commit()
                page = page + 1
                query_string = "fulfilment-method=" + fulfilment_by + "&" + "page=" + str(page)
                _logger.info("IMPORT ORDER PAGE COUNTER %s" % page)
                response_obj, response = BolAPI.get('orders', instance.bol_auth_token, query_string)
                if response_obj.status_code in [400, 401]:
                    instance.get_bol_token()
                    response_obj, response = BolAPI.get('orders', instance.bol_auth_token,
                                                        query_string)
                if response.get('orders'):
                    bol_order_queue_line_obj.create({'bol_order_data': json.dumps(response.get('orders')),
                                                     'bol_instance_id': instance.id,
                                                     'bol_order_data_queue_id': order_queue_id.id,
                                                     'bol_order_id': page,
                                                     'total_number_of_orders': len(response.get('orders'))})
                else:
                    _logger.info("Break loop because of response : %s" % response)
                    break
        except Exception as e:
            transaction_vals = {'message': e,
                                'log_book_id': log_rec.id}
            transaction_log_obj.create(transaction_vals)

        if not log_rec.log_lines:
            log_rec.unlink()

        if not order_queue_id.order_data_queue_line_ids:
            order_queue_list.remove(order_queue_id.id)
            order_queue_id.unlink()

        return order_queue_list

    def process_order_queue(self):
        """
        This method is used to process queue record
        :return:
        @author : Ekta Bhut
        """
        common_log_book_obj = self.env['common.log.book.ept']
        sale_obj = self.env['sale.order']
        model_id = self.env['ir.model']._get('bol.queue.ept').id
        log_book = common_log_book_obj.search([('model_id', '=', model_id), ('res_id', '=', self.id)])
        if len(log_book) > 1:
            log_book.unlink()

        if log_book and log_book.log_lines:
            log_book.log_lines.unlink()

        if not log_book:
            log_book_vals = {
                'type': 'import',
                'model_id': model_id,
                'res_id': self.id,
                'bol_instance_id': self.bol_instance_id.id,
                'module': 'bol_ept',
                'active': True
            }
            log_book = common_log_book_obj.create(log_book_vals)

        queue_line_ids = self.order_data_queue_line_ids.filtered(lambda line: line.state in ['draft', 'failed'])
        fulfilment_by = self.fulfilment_by
        for queue_line in queue_line_ids:
            sale_obj.process_bol_open_order_queue_line(self.bol_instance_id, queue_line,
                                                       fulfilment_by,
                                                       log_book)
            if not queue_line.bol_order_data:
                queue_line.write({'state': 'done'})
            queue_line._cr.commit()

        if log_book and not log_book.log_lines:
            log_book.unlink()

        status = self.order_data_queue_line_ids.filtered(lambda x: x.state in ('draft', 'failed'))
        if status:
            self.write({'state': 'partial'})
        else:
            self.write({'state': 'done'})
        return True

    @api.model
    def auto_process_open_order_queue(self):
        """
        This method is used to process all the open order queue.
        :return:
        """
        order_data_queue_ids = []

        query = """select queue.id
                    from bol_order_data_queue_line_ept as queue_line
                    inner join bol_queue_ept as queue on queue_line.bol_order_data_queue_id = queue.id
                    where queue_line.state='draft' and queue.is_action_require = 'False' 
                    GROUP BY queue.id,queue_line.create_date
                    ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        order_data_queue_list = self._cr.fetchall()
        if not order_data_queue_list:
            return

        for result in order_data_queue_list:
            order_data_queue_ids.append(result[0])

        queues = self.browse(list(set(order_data_queue_ids)))
        self.process_product_queue_and_post_message(queues)
        return True

    def process_product_queue_and_post_message(self, queues):
        """
        This method is used to post a message if the queue is process more than 3 times otherwise
        it calls the child method to process the product queue line.
        :param queues: Records of product queue.
        @author: Ekta Bhut
        """
        ir_model_obj = self.env["ir.model"]
        common_log_book_obj = self.env["common.log.book.ept"]
        start = time.time()
        product_queue_process_cron_time = queues.bol_instance_id.get_bol_cron_execution_time(
                "bol_ept.ir_cron_process_bol_open_order_queue")

        for queue in queues:
            queue.process_order_queue()
            # For counting the queue crashes and creating schedule activity for the queue.
            queue.queue_process_count += 1
            if queue.queue_process_count > 3:
                queue.is_action_require = True
                note = "<p>Need to process this product queue manually.There are 3 attempts been made by " \
                       "automated action to process this queue,<br/>- Ignore, if this queue is already processed.</p>"
                queue.message_post(body=note)
                if queue.bol_instance_id.is_bol_create_schedule:
                    model_id = ir_model_obj.search([("model", "=", "bol.queue.ept")]).id
                    common_log_book_obj.create_crash_queue_schedule_activity(queue, model_id, note)
                return True

            self._cr.commit()
            if time.time() - start > product_queue_process_cron_time - 60:
                return True
        return True

    @api.model
    def auto_import_fbr_open_order_queue(self, ctx={}):
        """
        This method is called from scheduler
        :param ctx: Argument
        :return:
        @author : Ekta Bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = ctx.get('bol_instance_id')
        if instance_id:
            instance = bol_instance_obj.browse(instance_id)
            self.import_order_queue(instance, 'FBR')

    @api.model
    def auto_import_fbb_open_order_queue(self, ctx={}):
        """
        This method is called from scheduler
        :param ctx: Argument
        :return:
        @author : Ekta Bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = ctx.get('bol_instance_id')
        if instance_id:
            instance = bol_instance_obj.browse(instance_id)
            self.import_order_queue(instance, 'FBB')
