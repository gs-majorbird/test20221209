# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

import json
import logging
import time
from datetime import datetime

from odoo import models, fields, api, _

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class BolShippedOrderQueue(models.Model):
    _name = 'bol.shipped.data.queue.ept'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'BOl Shipped Order Data Queue'
    _order = "create_date desc"

    name = fields.Char(size=120, string='Name')
    import_time = fields.Datetime('Imported at', default=lambda self: fields.Datetime.now())
    shipped_order_log_line_ids = fields.One2many('common.log.lines.ept',
                                                 'bol_shipped_order_queue_line_id',
                                                 compute="_compute_shipment_queue_log_lines",
                                                 string="Log Lines")
    bol_instance_id = fields.Many2one('bol.instance.ept', string='Bol Instance',
                                      help="Bol Instance")
    fulfilment_by = fields.Selection([('FBB', 'FBB'), ('FBR', 'FBR')], 'Fulfilment Method',
                                     readonly=True)
    is_process_queue = fields.Boolean('Is Processing Queue', default=False)
    running_status = fields.Char(default="Running...")
    is_action_require = fields.Boolean(default=False,
                                       help="it is used  to find the action require queue")
    queue_process_count = fields.Integer(string="Queue Process Times",
                                         help="it is used know queue how many time processed")
    log_count = fields.Integer(compute="get_log_count", string="Shipped Log Counter",
                               help="Count number of created shipped log", store=False)

    queue_line_total_record = fields.Integer(string='Total Records',
                                             compute='_compute_order_queue_line_record')
    queue_line_draft_record = fields.Integer(string='Draft Records',
                                             compute='_compute_order_queue_line_record')
    queue_line_fail_record = fields.Integer(string='Fail Records',
                                            compute='_compute_order_queue_line_record')
    queue_line_done_record = fields.Integer(string='Done Records',
                                            compute='_compute_order_queue_line_record')
    queue_line_cancel_record = fields.Integer(string='Cancel Records',
                                              compute='_compute_order_queue_line_record')
    shipped_order_data_queue_line_ids = fields.One2many('bol.shipped.data.queue.line.ept',
                                                        'bol_shipped_order_queue_id',
                                                        string="Shipped Order Queue Lines")
    state = fields.Selection([('draft', 'Draft'),
                              ('partial', 'Partically Completed'),
                              ('done', 'Done'),
                              ('failed', 'Failed')], default='draft')

    def _compute_shipment_queue_log_lines(self):
        """
        List Bol Orders Queue Log lines
        :return: Queue log line
        @author: Ekta bhut
        """
        for queue in self:
            log_book_obj = self.env['common.log.book.ept']
            model_id = self.env['ir.model']._get('bol.queue.ept').id
            domain = [('res_id', '=', queue.id), ('model_id', '=', model_id)]
            log_book_id = log_book_obj.search(domain)
            queue.shipped_order_log_line_ids = log_book_id and log_book_id[
                0].log_lines.ids or False

    def get_log_count(self):
        """
        Log count related queue job.
        :return: Log count
        @author: Ekta Bhut
        """
        model_id = self.env['ir.model']._get('bol.shipped.data.queue.ept').id
        log_obj = self.env['common.log.book.ept']
        self.log_count = log_obj.search_count([('res_id', '=', self.id), ('model_id', '=', model_id)])

    def list_of_process_logs(self):
        """
        This Method relocate mismatch log.
        @author: Ekta Bhut
        """
        bol_job_log_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.shipped.data.queue.ept').id
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

    @api.depends('shipped_order_data_queue_line_ids.state')
    def _compute_order_queue_line_record(self):
        """This is used for count of total records of order queue lines.
            @param : self
            @author: Ekta Bhut
        """
        for order_queue in self:
            queue_lines = order_queue.shipped_order_data_queue_line_ids
            order_queue.queue_line_total_record = len(queue_lines)
            order_queue.queue_line_draft_record = len(queue_lines.filtered(lambda x: x.state == "draft"))
            order_queue.queue_line_done_record = len(queue_lines.filtered(lambda x: x.state == "done"))
            order_queue.queue_line_fail_record = len(queue_lines.filtered(lambda x: x.state == "failed"))
            order_queue.queue_line_cancel_record = len(queue_lines.filtered(lambda x: x.state == "cancel"))

    @api.model
    def create(self, vals):
        """
        We generate the name of the queue in sequencial manner.
        :param vals: values provided to create a record
        :return: Newly created record with a newly generated sequence
        @author: Ekta Bhut
        """
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('bol.shipped.data.queue.ept') or 'New'
        result = super(BolShippedOrderQueue, self).create(vals)
        return result

    def activate_shipped_order_queue_cron(self, instance):
        """
        This Method is used to activate shipped order queue.
        :param instance:
        :return:
        """
        cron_exist = self.env.ref('bol_ept.ir_cron_auto_import_bol_shipped_order_queue_%d' % ( \
            instance.id), raise_if_not_found=False)
        vals = {'active': True,
                'interval_number': 10,
                'interval_type': 'minutes',
                'nextcall': datetime.now(),
                'user_id': self.env.user.id,
                'numbercall': 500,
                'code': "model.auto_import_shipped_order_queue({'bol_instance_id':%d})" % instance.id}
        if cron_exist:
            cron_exist.write(vals)
        else:
            import_shipment_cron = self.env.ref(
                    'bol_ept.ir_cron_auto_import_bol_shipped_order_queue', raise_if_not_found=False)
            if not import_shipment_cron:
                raise Warning(_(
                        'Core settings of BOl are deleted, please upgrade Bol.Com module to back this '
                        'settings.'))

            name = 'FBB-FBR ' + instance.name + ' : Import Shipped Order'
            vals.update({'name': name})
            new_cron = import_shipment_cron.copy(default=vals)
            self.env['ir.model.data'].create({'module': 'bol_ept',
                                              'name': 'ir_cron_auto_import_bol_shipped_order_queue_%d' % (
                                                  instance.id),
                                              'model': 'ir.cron',
                                              'res_id': new_cron.id,
                                              'noupdate': True})

        instance.write({'fbb_bol_shipped_page_number': 1, 'fbr_bol_shipped_page_number': 1})
        return True

    def auto_import_shipped_order_queue(self, args={}):
        """
        :param instance:
        :return:
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = args.get('bol_instance_id')
        instance = bol_instance_obj.browse(instance_id)
        fulfillment_by = instance.get_bol_instance_fulfillment_by()
        self.import_shipped_order_queue(instance, fulfillment_by)
        return True

    def import_shipped_order_queue(self, instance, fulfillment_by):
        """
        Create queue for open order
        :param instance: Bol Instance
        :param fulfillment_by: FBR & FBB
        :return: True
        """
        log_book_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.shipped.data.queue.ept').id
        for fulfillment in fulfillment_by:
            message = "Import %s shipped orders for Bol instance : %s" % (
                fulfillment, instance.name)
            log_rec = log_book_obj.bol_create_common_log_book('import', instance, model_id,
                                                              message, self.id)
            self.create_queue_for_shipped_orders(instance, fulfillment, log_rec)
            self._cr.commit()
        return True

    def create_queue_for_shipped_orders(self, instance, fulfilment_by, log_rec):
        """
        :param instance:
        :param fulfilment_by:
        :param log_rec:
        :return:
        """
        transaction_log_obj = self.env['common.log.lines.ept']
        bol_shipped_order_queue_line_obj = self.env['bol.shipped.data.queue.line.ept']
        shipped_order_queue_id = self.env['bol.shipped.data.queue.ept'].create({
            'bol_instance_id': instance.id, 'fulfilment_by': fulfilment_by})
        page = instance.fbb_bol_shipped_page_number if fulfilment_by == 'FBB' else \
            instance.fbr_bol_shipped_page_number or 1
        counter = 0
        cron_name = 'bol_ept.ir_cron_auto_import_bol_shipped_order_queue_%d' % instance.id
        start = time.time()
        execution_interval = instance.get_bol_cron_execution_time(cron_name)
        try:
            while True:
                counter += 1
                if counter == 11:
                    shipped_order_queue_id = self.env['bol.shipped.data.queue.ept'].create({
                        'bol_instance_id': instance.id, 'fulfilment_by': fulfilment_by})
                    counter = 0
                    self._cr.commit()
                if page < 0:
                    page = 1
                _logger.info('PROCESSING SHIPMENT PAGE COUNTER %s', page)
                query_string = "fulfilment-method=" + fulfilment_by + "&" + "page=" + str(page)
                _logger.info("IMPORT ORDER PAGE COUNTER %s , %s" % (page, fulfilment_by))
                response_obj, response = BolAPI.get('shipment_list', instance.bol_auth_token,
                                                    query_string)
                if response_obj.status_code in [400, 401]:
                    time.sleep(5)
                    instance.get_bol_token()
                    response_obj, shipped_order_data = BolAPI.get('shipment_list',
                                                                  instance.bol_auth_token,
                                                                  query_string)

                if response_obj.status_code == 429:
                    time.sleep(5)
                    continue
                if response.get('shipments'):
                    bol_shipped_order_queue_line_obj.create({
                        'bol_order_id': page,
                        'bol_shipped_data': json.dumps(response.get('shipments')),
                        'bol_instance_id': instance.id,
                        'fulfillment_by': fulfilment_by,
                        'bol_shipped_order_queue_id': shipped_order_queue_id.id,
                        'total_number_of_orders': len(response.get('shipments'))})
                    page = page + 1
                else:
                    _logger.info("Break loop because of response : %s" % response)
                    if fulfilment_by == 'FBB':
                        instance.write({'fbb_bol_shipped_page_number': page})
                    else:
                        instance.write({'fbr_bol_shipped_page_number': page})
                    break
                if time.time() - start > execution_interval - 100:
                    if fulfilment_by == 'FBB':
                        instance.write({'fbb_bol_shipped_page_number': page})
                    else:
                        instance.write({'fbr_bol_shipped_page_number': page})
                    self._cr.commit()
                    break

        except Exception as e:
            transaction_vals = {'message': e,
                                'log_book_id': log_rec.id}
            transaction_log_obj.create(transaction_vals)

        if not shipped_order_queue_id.shipped_order_data_queue_line_ids:
            shipped_order_queue_id.unlink()

        return True

    def process_order_queue(self):
        common_log_book_obj = self.env['common.log.book.ept']
        sale_obj = self.env['sale.order']
        model_id = self.env['ir.model']._get('bol.shipped.data.queue.ept').id
        log_book = common_log_book_obj.search(
                [('model_id', '=', model_id), ('res_id', '=', self.id)])
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

        queue_line_ids = self.shipped_order_data_queue_line_ids.filtered(
                lambda line: line.state in ['draft', 'failed'])
        fulfilment_by = self.fulfilment_by
        count = 0
        for queue_line in queue_line_ids:
            count = count + 1
            if count == 10:
                count = 0
                self._cr.commit()
            sale_obj.process_bol_shipped_order_queue_line(self.bol_instance_id, queue_line,
                                                          fulfilment_by,
                                                          log_book)
            queue_line.write({'state': 'done'})
            queue_line._cr.commit()

        if log_book and not log_book.log_lines:
            log_book.unlink()

        status = self.shipped_order_data_queue_line_ids.filtered(
                lambda x: x.state in ('draft', 'failed'))
        if status:
            self.write({'state': 'partial'})
        else:
            self.write({'state': 'done'})
        return True

    @api.model
    def auto_process_shipped_order_queue(self):
        """
        This method is used to process all the open order queue.
        :return:
        """
        shipped_order_data_queue_ids = []

        query = """select queue.id
                    from bol_shipped_data_queue_line_ept as queue_line
                    inner join bol_shipped_data_queue_ept as queue on queue_line.bol_shipped_order_queue_id = queue.id
                    where queue_line.state='draft' and queue.is_action_require = 'False' 
                    GROUP BY queue.id,queue_line.create_date
                    ORDER BY queue_line.create_date ASC"""
        self._cr.execute(query)
        shipped_order_data_queue_data = self._cr.fetchall()
        if not shipped_order_data_queue_data:
            return

        for result in shipped_order_data_queue_data:
            shipped_order_data_queue_ids.append(result[0])

        queues = self.browse(list(set(shipped_order_data_queue_ids)))
        self.process_product_queue_and_post_message(queues)
        return

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
                "bol_ept.ir_cron_process_bol_shipped_order_queue")

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
                    model_id = ir_model_obj.search([("model", "=", "bol.shipped.data.queue.ept")]).id
                    common_log_book_obj.create_crash_queue_schedule_activity(queue, model_id, note)
                return True

            self._cr.commit()
            if time.time() - start > product_queue_process_cron_time - 60:
                return True
        return True
