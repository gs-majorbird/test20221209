# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class IrCron(models.Model):
    _inherit = 'ir.cron'

    bol_instance_cron_id = fields.Many2one('bol.instance.ept', string="BOL Cron Scheduler")
