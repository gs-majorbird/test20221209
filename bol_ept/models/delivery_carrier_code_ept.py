# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class BolDeliveryCarrierCode(models.Model):
    _name = 'bol.delivery.carrier.code.ept'
    _description = 'Bol Delivery Carrier Code'

    name = fields.Char()
    code = fields.Char()
