# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields, models

class SaleReport(models.Model):
    _inherit = "sale.report"

    bol_instance_id = fields.Many2one("bol.instance.ept", "Bol Instance", copy=False, readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        """ Inherit the query here to add the bol instance field for group by.
        @author : Ekta Bhut
        """
        fields['bol_instance_id'] = ", s.bol_instance_id as bol_instance_id"
        groupby += ', s.bol_instance_id'
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)

    def bol_sale_report(self):
        """ Base on the odoo version it return the action.
            @author : Ekta Bhut
        """
        version_info = odoo.service.common.exp_version()
        if version_info.get('server_version') == '14.0':
            action = self.env.ref('bol_ept.bol_action_order_report_all').read()[0]
        else:
            action = self.env.ref('bol_ept.bol_sale_report_action_dashboard').read()[0]

        return action
