# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime, timedelta

from odoo import models, fields

_logger = logging.getLogger(__name__)

class CommonLogBookEpt(models.Model):
    _inherit = "common.log.book.ept"

    bol_instance_id = fields.Many2one("bol.instance.ept", "Instance")

    def bol_create_common_log_book(self, process_type, instance, model_id, message, res_id):
        """
        This method used to create a log book record.
        :param type: Generally, the type value is 'import' or 'export'.
        :model_id: record of model.
        @return: log_book_id
        @author: Ekta Bhut
        """
        log_book_id = self.create({"type": process_type,
                                   "module": "bol_ept",
                                   "bol_instance_id": instance.id if instance else False,
                                   "model_id": model_id,
                                   "active": True,
                                   "res_id": res_id,
                                   "message": message})
        return log_book_id

    def create_crash_bol_queue_schedule_activity(self, queue_id, model_id, note):
        """
        This method is used to create a schedule activity for the queue crash.
        Base on the Bol configuration when any queue crash will create a schedule activity.
        :param queue_id: Record of the queue(customer,product and order)
        :param model_id: Record of model
        :param note: Message
        @author:Ekta Bhut
        """
        mail_activity_obj = self.env['mail.activity']
        activity_type_id = queue_id and queue_id.bol_instance_id.bol_activity_type_id.id
        date_deadline = datetime.strftime(
                datetime.now() + timedelta(days=int(queue_id.bol_instance_id.bol_date_deadline)), "%Y-%m-%d")

        if queue_id:
            for user_id in queue_id.bol_instance_id.bol_user_ids:
                mail_activity = mail_activity_obj.search(
                        [('res_model_id', '=', model_id), ('user_id', '=', user_id.id), ('res_id', '=', queue_id.id),
                         ('activity_type_id', '=', activity_type_id)])
                if not mail_activity:
                    vals = self.prepare_vals_for_bol_schedule_activity(activity_type_id, note, queue_id, user_id,
                                                                       model_id,
                                                                       date_deadline)
                    try:
                        mail_activity_obj.create(vals)
                    except:
                        _logger.info("Unable to create schedule activity, Please give proper "
                                     "access right of this user :%s  ", user_id.name)
        return True

    def prepare_vals_for_bol_schedule_activity(self, activity_type_id, note, queue_id, user_id, model_id,
                                               date_deadline):
        """ This method used to prepare a vals for the schedule activity.
            :param activity_type_id: Record of the activity type(email,call,meeting, to do)
            :param user_id: Record of user(whom to assign schedule activity)
            :param date_deadline: date of schedule activity dead line.
            @return: values
            @author:Ekta Bhut
        """
        values = {'activity_type_id': activity_type_id,
                  'note': note,
                  'res_id': queue_id.id,
                  'user_id': user_id.id or self._uid,
                  'res_model_id': model_id,
                  'date_deadline': date_deadline
                  }
        return values
