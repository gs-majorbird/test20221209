# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

""" Usage : Inherit the model res company and added and manage the functionality of Onboarding Panel"""
from odoo import fields, models, api

BOL_ONBOARDING_STATES = [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"),
                         ('closed', "Closed")]


class ResCompany(models.Model):
    """
        Inherit Class and added and manage the functionality of Onboarding (Banner) Panel
    """
    _inherit = 'res.company'

    # BOL Onboarding Panel
    bol_onboarding_state = fields.Selection(selection=BOL_ONBOARDING_STATES,
                                            string="State of the bol onboarding panel", default='not_done')
    bol_instance_onboarding_state = fields.Selection(selection=BOL_ONBOARDING_STATES,
                                                     string="State of the bol instance onboarding panel",
                                                     default='not_done')
    bol_basic_configuration_onboarding_state = fields.Selection(BOL_ONBOARDING_STATES, default='not_done',
                                                                string="State of the bol basic configuration "
                                                                       "onboarding step")
    bol_general_configuration_onboarding_state = fields.Selection(BOL_ONBOARDING_STATES, default='not_done',
                                                             string="State of the onboarding bol financial "
                                                                    "status step")
    bol_cron_configuration_onboarding_state = fields.Selection(BOL_ONBOARDING_STATES, default='not_done',
                                                               string="State of the onboarding bol cron "
                                                                      "configurations step")
    is_create_bol_more_instance = fields.Boolean(string='Is create bol more instance?', default=False)
    bol_onboarding_toggle_state = fields.Selection(selection=[('open', "Open"), ('closed', "Closed")],
                                                   default='open')

    @api.model
    def action_close_bol_instances_onboarding_panel(self):
        """ Mark the onboarding panel as closed.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        self.env.company.bol_onboarding_state = 'closed'

    def get_and_update_bol_instances_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        steps = [
            'bol_instance_onboarding_state',
            'bol_basic_configuration_onboarding_state',
            'bol_general_configuration_onboarding_state',
            'bol_cron_configuration_onboarding_state',
        ]
        return self.get_and_update_onbarding_state('bol_onboarding_state', steps)

    def action_toggle_bol_instances_onboarding_panel(self):
        """ To change and pass the value of selection of current company to hide / show panel.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        self.bol_onboarding_toggle_state = 'closed' if self.bol_onboarding_toggle_state == 'open' else 'open'
        return self.bol_onboarding_toggle_state
