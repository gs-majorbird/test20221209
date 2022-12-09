# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class BolOnboarding(http.Controller):
    @http.route('/bol_instances/bol_instances_onboarding_panel', auth='user', type='json')
    def bol_instances_onboarding_panel(self):
        """ Returns the `banner` for the bol onboarding panel.It can be empty if the user has closed it or if he
            doesn't have the permission to see it.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        current_company_id = request.httprequest.cookies.get('cids').split(',') if request.httprequest.cookies.get(
            'cids', []) else []
        company = False
        if len(current_company_id) > 0 and current_company_id[0] and current_company_id[0].isdigit():
            company = request.env['res.company'].sudo().search([('id', '=', int(current_company_id[0]))])
        if not company:
            company = request.env.company
        hide_panel = company.bol_onboarding_toggle_state != 'open'
        btn_value = 'Create More Bol Instance' if hide_panel else 'Hide On boarding Panel'
        bol_manager_group = request.env.ref("bol_ept.group_bol_manager_ept")
        if request.env.uid not in bol_manager_group.users.ids:
            return {}
        return {
            'html': request.env.ref('bol_ept.bol_instances_onboarding_panel_ept')._render({
                'company': company,
                'toggle_company_id': company.id,
                'hide_panel': hide_panel,
                'btn_value': btn_value,
                'state': company.get_and_update_bol_instances_onboarding_state(),
                'is_button_active': company.is_create_bol_more_instance
            })
        }
