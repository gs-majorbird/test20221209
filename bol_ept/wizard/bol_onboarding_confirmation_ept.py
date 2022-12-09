# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, _


class BolOnboardingConfirmationEpt(models.TransientModel):
    _name = 'bol.onboarding.confirmation.ept'
    _description = 'Bol Onboarding Confirmation'

    def done_all_configuration(self):
        """ Save the Cron Changes by Instance Wise.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        instance_id = self._context.get('bol_instance_id', False)
        if instance_id:
            instance = self.env['bol.instance.ept'].browse(instance_id)
            company = instance.company_id
            company.write({
                'bol_instance_onboarding_state': 'not_done',
                'bol_basic_configuration_onboarding_state': 'not_done',
                'bol_general_configuration_onboarding_state': 'not_done',
                'bol_cron_configuration_onboarding_state': 'not_done',
                'is_create_bol_more_instance': False
            })
            instance.write({'is_onboarding_configurations_done': True})
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': _(
                        "Congratulations, You have done All Configurations of the instance: {}".format(instance.name)),
                    'img_url': '/web/static/src/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def remaining_configuration(self):
        """ Unsave the changes and reload the page.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
