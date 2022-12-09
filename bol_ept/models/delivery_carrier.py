# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    bol_delivery_carrier_code_id = fields.Many2one('bol.delivery.carrier.code.ept',
                                                   string="Bol Delivery Code")
