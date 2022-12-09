# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    bol_fulfillment_by = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB')], 'fulfilment Method',
                                          readonly=True)
    bol_instance_id = fields.Many2one('bol.instance.ept', "Bol Instance")
