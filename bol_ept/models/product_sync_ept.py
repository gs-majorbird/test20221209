# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

import base64
import csv
import logging
import time
from _io import StringIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class BolProductSync(models.Model):
    _name = 'bol.product.sync.ept'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Bol Product Sync report'

    bol_instance_id = fields.Many2one('bol.instance.ept', string='Instance',
                                      domain=[('state', 'in', ['confirmed'])])
    name = fields.Char(size=256, string='Reference', default="New")
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    requested_date = fields.Datetime('Requested Date', default=time.strftime("%Y-%m-%d %H:%M:%S"))
    state = fields.Selection(
            [('draft', 'Draft'), ('requested', 'Requested'), ('downloaded', 'Downloaded'),
             ('processed', 'Processed')],
            string='Process Status', default='draft')
    user_id = fields.Many2one('res.users', string="Requested User")
    file_url = fields.Char('File Url')
    export_offer_file_id = fields.Char('Export offer file id')
    entity_id = fields.Char('Entity Id')
    update_price_in_pricelist = fields.Boolean(string='Update price in pricelist?', default=False,
                                               help='Update or create product line in pricelist if ticked.')
    auto_create_product = fields.Boolean(string='Auto create product?', default=False,
                                         help='Create product in ERP if not found.')
    is_hide_mismatch_detail_button = fields.Boolean("Is Hide button", default=False, compute="_compute_is_mismatch")

    @api.depends('state')
    def _compute_is_mismatch(self):
        log_book_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.product.sync.ept').id
        for record in self:
            bol_job = log_book_obj.search(
                    [('res_id', '=', record.id), ('model_id', '=', model_id), ('bol_instance_id', '=',
                                                                               record.bol_instance_id.id)])
            if bol_job.log_lines:
                record.write({'is_hide_mismatch_detail_button': True})
            else:
                record.write({'is_hide_mismatch_detail_button': False})

    @api.model
    def create(self, vals):
        """
        :vals : record creation vals
        This method will be used for set sequence as name.
        @author : Ekta Bhut , 16th March 2021
        """
        try:
            sequence = self.env.ref("bol_ept.seq_bol_product_sync_job")
        except Exception as e:
            sequence = False
        name = sequence and sequence.next_by_id() or '/'
        vals.update({'name': name, 'user_id': self.env.user.id})
        return super(BolProductSync, self).create(vals)

    def unlink(self):
        """
        if product sync report is processed then give warning while unlink record.
        """
        for report in self:
            if report.state == 'processed':
                raise UserError(_('You cannot delete processed record.'))
        return super(BolProductSync, self).unlink()

    def get_bol_product_sync_report(self):
        """
        This method is used to get product sync report from Bol.com
        :return: response object, result
        @author : Ekta Bhut, 16th March 2021
        """
        response_obj, result = BolAPI.post('export_offer_file',
                                           self.bol_instance_id.bol_auth_token, {"format": "CSV"})
        if response_obj.status_code == 401:
            self.bol_instance_id.get_bol_token()
            response_obj, result = BolAPI.post('export_offer_file',
                                               self.bol_instance_id.bol_auth_token, {"format": "CSV"})
        return response_obj, result

    def get_processed_product_sync_report(self):
        """
        This method is used to get report entity id from Bol.com
        :return: Response Object, Result
        @author : Ekta Bhut, 16th March 2021
        """
        request_process_obj, result = BolAPI.get('process_status',
                                                 self.bol_instance_id.bol_auth_token, self.export_offer_file_id)
        return request_process_obj, result

    def get_product_report_file(self):
        """
        This method is used to get CSV report from Bol.com
        :return: Response Onject, Result
        @author : Ekta Bhut, 16th March 2021
        """
        response_obj, result = BolAPI.get_csv('offer_file',
                                              self.bol_instance_id.bol_auth_token, self.entity_id)
        return response_obj, result

    def request_file(self):
        """
        This method is used to request file for product.
        :return: True
        @author : Ekta bhut , 16th March 2021
        """
        vals = {}
        log_book_obj = self.env['common.log.book.ept']
        request_process_obj = False
        get_process_status_dict = {}
        model_id = self.env['ir.model']._get('bol.product.sync.ept').id
        message = "Perform Operation for Retrive Product Export file from bol.com"
        bol_job = log_book_obj.search([('res_id', '=', self.id), ('model_id', '=', model_id), ('bol_instance_id', '=',
                                                                                               self.bol_instance_id.id)])
        if not bol_job:
            bol_job = log_book_obj.bol_create_common_log_book('import', self.bol_instance_id, model_id,
                                                              message, self.id)
        try:
            if not self.export_offer_file_id:
                response_obj, result = self.get_bol_product_sync_report()
                if response_obj.status_code == 202:
                    self.export_offer_file_id = result.get('processStatusId')
                    request_process_obj, get_process_status_dict = self.get_processed_product_sync_report()
            else:
                self.bol_instance_id.get_bol_token()
                request_process_obj, get_process_status_dict = self.get_processed_product_sync_report()
        except Exception as e:
            bol_job and bol_job.write({'log_lines': [(0, 0, {'message': e})]})
            return True
        if request_process_obj and request_process_obj.status_code == 200:
            entity_id = get_process_status_dict.get('entityId')
            entity_id and vals.update({'entity_id': entity_id, 'state': 'requested'})
            vals and self.write(vals)
        if not bol_job.log_lines:
            bol_job.unlink()
        return True

    def get_file(self):
        """
        This method is used to get file for product.
        :return: True
        @author : Ekta bhut , 16th March 2021
        """
        log_book_obj = self.env['common.log.book.ept']
        if not self.entity_id:
            raise Warning(_('Entity Id does not exists, Please first request product file'))
        bol_instance_id = self.bol_instance_id
        model_id = self.env['ir.model']._get('bol.product.sync.ept').id
        message = "Perform Operation for Get Product file from bol.com"
        bol_job = log_book_obj.search([('res_id', '=', self.id), ('model_id', '=', model_id), ('bol_instance_id', '=',
                                                                                               self.bol_instance_id.id)])
        if not bol_job:
            bol_job = log_book_obj.bol_create_common_log_book('import', self.bol_instance_id, model_id,
                                                              message, self.id)
        try:
            response_obj, response = self.get_product_report_file()
            if response_obj.status_code == 401:
                bol_instance_id.get_bol_token()
                response_obj, response = self.get_product_report_file()
        except Exception as e:
            bol_job.write({'log_lines': [(0, 0, {'message': e})]})
            return True
        if not response.__contains__(
                "offerId,ean,conditionName,conditionCategory,conditionComment,bundlePricesPrice,"
                "fulfilmentDeliveryCode,stockAmount,onHoldByRetailer,fulfilmentType,mutationDateTime,referenceCode"):
            bol_job.write({'log_lines': [(0, 0, {'message': "Response not in proper format\n%s" % response})]})
            return True
        if response_obj.status_code == 200:
            file_name = self.name + time.strftime("%Y_%m_%d_%H%M%S") + "_offers.csv"
            attachment = self.env['ir.attachment'].create({
                'name': file_name, 'res_model': 'mail.compose.message', 'type': 'binary',
                'datas': base64.b64encode(response.encode(encoding='utf_8', errors='strict'))})
            self.sudo().message_post(body=_("<b>Product File Downloaded</b>"), attachment_ids=attachment.ids)
            self.write({'attachment_id': attachment.id, 'state': 'downloaded'})
        if not bol_job.log_lines:
            bol_job.unlink()
        return True

    def process_file(self):
        """
        This method is used to process file for product.
        :return: True
        @author : Ekta bhut , 16th March 2021
        """
        if not self.attachment_id:
            raise Warning(_("There is no any report are attached with this record."))
        if not self.bol_instance_id:
            raise Warning(_("Instance not found "))

        imp_file = StringIO(base64.b64decode(self.attachment_id.datas).decode())
        reader = csv.DictReader(imp_file, delimiter=',')
        model_id = self.env['ir.model']._get('bol.product.sync.ept').id,
        log_book_obj = self.env['common.log.book.ept']
        transaction_log_obj = self.env['common.log.lines.ept']
        bol_offer_obj = self.env['bol.offer.ept']
        log_rec = log_book_obj.search([('res_id', '=', self.id), ('model_id', '=', model_id), ('bol_instance_id', '=',
                                                                                               self.bol_instance_id.id)])
        if not log_rec:
            log_rec = log_book_obj.bol_create_common_log_book('import', self.bol_instance_id, model_id,
                                                              "", self.id)

        instance_id = self.bol_instance_id
        for row in reader:
            bol_offer_id = row.get('offerId') or ''
            _logger.info("processing bol product with offer id %s", bol_offer_id)
            bol_offer_obj.sync_product(instance_id, log_rec, bol_offer_id, self.update_price_in_pricelist,
                                       self.auto_create_product)

        self.write({'state': 'processed'})
        if not log_rec.log_lines:
            log_rec.unlink()
        return True

    def list_of_logs(self):
        """
        This Method relocate mismatch log.
        """
        bol_job_log_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('bol.product.sync.ept').id
        records = bol_job_log_obj.search(
                [('model_id', '=', model_id),
                 ('res_id', '=', self.id), ('bol_instance_id', '=', self.bol_instance_id.id)])
        action = {
            'domain': "[('id', 'in', " + str(records.ids) + " )]",
            'name': 'Mismatch Logs',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'common.log.book.ept',
            'type': 'ir.actions.act_window',
        }
        return action
