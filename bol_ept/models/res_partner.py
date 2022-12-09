# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_bol_customer = fields.Boolean("Is Bol Customer?")
