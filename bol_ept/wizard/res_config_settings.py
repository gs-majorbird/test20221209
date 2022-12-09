# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo import SUPERUSER_ID


class ResConfigSettings(models.TransientModel):
    """
    @author: Maulik Barad on Date 12-Feb-2021.
    """
    _inherit = "res.config.settings"

    bol_instance_id = fields.Many2one("bol.instance.ept", "Instance")
    bol_company_id = fields.Many2one("res.company", string="Bol Company", related="bol_instance_id.company_id",
                                     store=False, help="Orders and Invoices will be generated of this company.")
    bol_fulfillment_by = fields.Selection([("FBR", "FBR"), ("FBB", "FBB"), ("Both", "FBR & FBB")],
                                          string="Fulfilment By", default="FBR")
    bol_fbr_warehouse_id = fields.Many2one("stock.warehouse", "FBR Warehouse")
    bol_fbb_warehouse_id = fields.Many2one("stock.warehouse", "FBB Warehouse")
    bol_pricelist_id = fields.Many2one("product.pricelist", "Price List")
    bol_lang_id = fields.Many2one("res.lang", "Language")
    bol_auto_create_product = fields.Boolean("Automatically Create Odoo Product If Not Found?", default=False)
    bol_payment_term_id = fields.Many2one("account.payment.term", "Bol Payment Term")
    is_default_sequence_fbr_sales_order = fields.Boolean("Use Default Odoo Sequence in FBR Sales Orders")
    is_default_sequence_fbb_sales_order = fields.Boolean("Use Default Odoo Sequence in FBB Sales Orders")
    bol_team_id = fields.Many2one("crm.team", "Sales Team")
    fbr_bol_order_prefix = fields.Char("FBR Order Prefix")
    fbb_bol_order_prefix = fields.Char("FBB Order Prefix")
    bol_import_order_after_date = fields.Datetime("Import Order After date", help="System will "
                                                                                  "import only those orders which are created after this date.")
    fbr_auto_workflow_id = fields.Many2one("sale.workflow.process.ept", string="Auto Workflow (FBR)")
    fbb_auto_workflow_id = fields.Many2one("sale.workflow.process.ept", string="Auto Workflow (FBB)")
    bol_import_shipment_order_type = fields.Selection([("FBB", "FBB"), ("FBR", "FBR"), ("Both", "FBR & FBB")],
                                                      "Import Shipment for", default="Both")
    bol_instance_stock_field = fields.Selection([("free_qty", "Free Quantity"),
                                                 ("virtual_available", "Forecast Quantity")],
                                                string="Export Stock Type")
    bol_inventory_last_sync_on = fields.Datetime(string="Last stock export date", help="Last stock "
                                                                                       "export date'")
    bol_auto_validate_inventory = fields.Boolean(string="Auto validate inventory")
    is_bol_create_schedule = fields.Boolean("Create Schedule Activity ? ", default=False,
                                            help="If checked, Then Schedule Activity create on order data queues"
                                                 " will any queue line failed.")
    bol_user_ids = fields.Many2many("res.users", "bol_res_config_setting_res_users_rel",
                                    "res_config_id", "res_users_id", string="Responsible User")
    bol_activity_type_id = fields.Many2one("mail.activity.type", string="Bol Activity Type")
    bol_date_deadline = fields.Integer("Deadline Lead Days for Bol", default=1,
                                       help="its add number of  days in schedule activity deadline date ")

    @api.onchange('bol_instance_id')
    def onchange_bol_instance_id(self):
        """
        This method sets configurations from the Instance, any Instance is selected.
        @author: Maulik Barad on Date 15-Feb-2021.
        """
        bol_instance_id = self.bol_instance_id
        if bol_instance_id:
            self.bol_fbr_warehouse_id = bol_instance_id.bol_fbr_warehouse_id.id or False
            self.bol_fbb_warehouse_id = bol_instance_id.bol_fbb_warehouse_id.id or False
            self.bol_company_id = bol_instance_id.company_id.id or False
            self.bol_lang_id = bol_instance_id.bol_lang_id.id or False
            self.fbr_bol_order_prefix = bol_instance_id.fbr_bol_order_prefix or ''
            self.fbb_bol_order_prefix = bol_instance_id.fbb_bol_order_prefix or ''
            self.bol_pricelist_id = bol_instance_id.bol_pricelist_id.id or False
            self.bol_payment_term_id = bol_instance_id.bol_payment_term_id.id or False
            self.bol_team_id = bol_instance_id.bol_team_id.id or False
            self.bol_auto_create_product = bol_instance_id.bol_auto_create_product
            self.bol_fulfillment_by = bol_instance_id.bol_fulfillment_by or False
            self.fbr_auto_workflow_id = bol_instance_id.fbr_auto_workflow_id or False
            self.fbb_auto_workflow_id = bol_instance_id.fbb_auto_workflow_id or False
            self.is_default_sequence_fbr_sales_order = bol_instance_id.is_default_sequence_fbr_sales_order or False
            self.is_default_sequence_fbb_sales_order = bol_instance_id.is_default_sequence_fbb_sales_order or False
            self.bol_import_shipment_order_type = bol_instance_id.bol_import_shipment_order_type or False
            self.bol_instance_stock_field = bol_instance_id.stock_field
            self.bol_inventory_last_sync_on = bol_instance_id.inventory_last_sync_on
            self.bol_auto_validate_inventory = bol_instance_id.auto_validate_inventory
            self.bol_import_order_after_date = bol_instance_id.bol_import_order_after_date
            self.is_bol_create_schedule = bol_instance_id.is_bol_create_schedule
            self.bol_user_ids = bol_instance_id.bol_user_ids or False
            self.bol_activity_type_id = bol_instance_id.bol_activity_type_id.id or False
            self.bol_date_deadline = bol_instance_id.bol_date_deadline or False

    def execute(self):
        """
        Saves the configurations into Instance.
        @author: Maulik Barad on Date 15-Feb-2021.
        """
        bol_instance_id = self.bol_instance_id
        values = {}
        res = super(ResConfigSettings, self).execute()
        if bol_instance_id:
            values['bol_fbr_warehouse_id'] = self.bol_fbr_warehouse_id.id if self.bol_fbr_warehouse_id else False
            values['bol_fbb_warehouse_id'] = self.bol_fbb_warehouse_id.id if self.bol_fbb_warehouse_id else False
            values['bol_lang_id'] = self.bol_lang_id.id if self.bol_lang_id else False
            values['fbr_bol_order_prefix'] = self.fbr_bol_order_prefix and self.fbr_bol_order_prefix
            values['fbb_bol_order_prefix'] = self.fbb_bol_order_prefix and self.fbb_bol_order_prefix
            values['bol_pricelist_id'] = self.bol_pricelist_id.id if self.bol_pricelist_id else False
            values['bol_payment_term_id'] = self.bol_payment_term_id.id if self.bol_payment_term_id else False
            values['bol_team_id'] = self.bol_team_id.id if self.bol_team_id else False
            values['bol_auto_create_product'] = self.bol_auto_create_product
            values['bol_fulfillment_by'] = self.bol_fulfillment_by
            values['fbr_auto_workflow_id'] = self.fbr_auto_workflow_id.id or False
            values['fbb_auto_workflow_id'] = self.fbb_auto_workflow_id.id or False
            values['is_default_sequence_fbr_sales_order'] = self.is_default_sequence_fbr_sales_order or False
            values['is_default_sequence_fbb_sales_order'] = self.is_default_sequence_fbb_sales_order or False
            values['bol_import_shipment_order_type'] = self.bol_import_shipment_order_type or False
            values['stock_field'] = self.bol_instance_stock_field
            values['inventory_last_sync_on'] = self.bol_inventory_last_sync_on
            values['auto_validate_inventory'] = self.bol_auto_validate_inventory
            values['bol_import_order_after_date'] = self.bol_import_order_after_date
            values['is_bol_create_schedule'] = self.is_bol_create_schedule
            values['bol_user_ids'] = [(6, 0, self.bol_user_ids.ids)]
            values['bol_activity_type_id'] = self.bol_activity_type_id.id or False
            values['bol_date_deadline'] = self.bol_date_deadline or False

            bol_instance_id.write(values)
        return res

    def set_values(self):
        """

        @return:
        """
        res = super(ResConfigSettings, self).set_values()
        bol_instance_obj = self.env['bol.instance.ept']
        bol_fulfillment_by = self.bol_fulfillment_by
        instance_id = self.bol_instance_id
        if bol_fulfillment_by == 'FBR':
            other_seller = bol_instance_obj.search([('id', '!=', instance_id.id), ('bol_fulfillment_by', '=', 'Both')])
            seller_company = other_seller.filtered(lambda x: x.company_id.id in self.env.user.company_ids.ids)
            if other_seller and seller_company:
                return True
            else:
                other_seller = bol_instance_obj.search([('id', '!=', instance_id.id),
                                                        ('bol_fulfillment_by', '=', 'FBB')])
                seller_company = other_seller.filtered(lambda x: x.company_id.id in self.env.user.company_ids.ids)
                if other_seller and seller_company:
                    bol_fulfillment_by = 'Both'
        elif bol_fulfillment_by == 'FBB':
            other_seller = bol_instance_obj.search([('id', '!=', instance_id.id), ('bol_fulfillment_by', '=', 'Both')])
            seller_company = other_seller.filtered(lambda x: x.company_id.id in self.env.user.company_ids.ids)
            if other_seller and seller_company:
                return True
            else:
                other_seller = bol_instance_obj.search([('id', '!=', instance_id.id),
                                                        ('bol_fulfillment_by', '=', 'FBR')])
                seller_company = other_seller.filtered(lambda x: x.company_id.id in self.env.user.company_ids.ids)
                if other_seller and seller_company:
                    bol_fulfillment_by = 'Both'

        self_sudo = self.with_user(SUPERUSER_ID)
        bol_fbr_group = self_sudo.env.ref('bol_ept.group_bol_fbr_ept')
        bol_fbb_group = self_sudo.env.ref('bol_ept.group_bol_fbb_ept')
        bol_fbr_fbb_group = self_sudo.env.ref('bol_ept.group_bol_fbr_and_fbb_ept')
        bol_user_group = self_sudo.env.ref('bol_ept.group_bol_user_ept')
        bol_manager_group = self_sudo.env.ref('bol_ept.group_bol_manager_ept')
        user_list = list(set(bol_user_group.users.ids + bol_manager_group.users.ids))

        if bol_fulfillment_by == 'FBR':
            bol_fbr_group.write({'users': [(6, 0, user_list)]})
            bol_fbb_group.write({'users': [(6, 0, [])]})
            bol_fbr_fbb_group.write({'users': [(6, 0, [])]})
        elif bol_fulfillment_by == 'FBB':
            bol_fbb_group.write({'users': [(6, 0, user_list)]})
            bol_fbr_group.write({'users': [(6, 0, [])]})
            bol_fbr_fbb_group.write({'users': [(6, 0, [])]})
        elif bol_fulfillment_by == 'Both':
            bol_fbr_fbb_group.write({'users': [(6, 0, user_list)]})
            bol_fbb_group.write({'users': [(6, 0, user_list)]})
            bol_fbr_group.write({'users': [(6, 0, user_list)]})

        return res

    # Below method are use for the onboarding panel

    @api.model
    def action_open_bol_instance_wizard(self):
        """ This action is used to set default value in the instance wizard of on boarding panel.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bol_ept.bol_on_board_instance_configuration_action")
        action['context'] = {'is_calling_from_onboarding_panel': True}
        instance = self.env['bol.instance.ept'].search_bol_instance()
        if instance:
            action.get('context').update({
                'default_name': instance.name,
                'default_client_id': instance.client_id,
                'default_secret_id': instance.secret_id,
                'default_bol_fulfillment_by': instance.bol_fulfillment_by,
                'default_bol_country_id': instance.bol_country_id.id,
                'default_company_id': instance.company_id.id,
                'is_already_instance_created': True,
            })
            company = instance.company_id
            if company.bol_instance_onboarding_state != 'done':
                company.set_onboarding_step_done('bol_instance_onboarding_state')
        return action

    @api.model
    def action_bol_open_basic_fbr_and_fbb_configuration_wizard(self):
        """ Prepare the action for open the basic FBR and FBR configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        try:
            view_id = self.env.ref('bol_ept.bol_basic_fbr_and_fbb_configurations_onboarding_wizard_view')
        except:
            return True
        return self.bol_fbb_and_fbb_res_config_view_action(view_id)

    @api.model
    def action_bol_open_general_configuration_wizard(self):
        """ Prepare the action for open the general configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 30 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        try:
            view_id = self.env.ref('bol_ept.bol_general_configurations_onboarding_wizard_view')
        except:
            return True
        return self.bol_fbb_and_fbb_res_config_view_action(view_id)

    @api.model
    def action_bol_open_cron_configuration_wizard(self):
        """ Prepare the action for open the general configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 30 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        try:
            view_id = self.env.ref('bol_ept.bol_cron_configuration_ept_form_view')
        except:
            return True
        return self.bol_cron_config_view_action(view_id)

    def bol_save_fbr_and_fbb_configurations(self):
        """ Save the basic configuration of fbb and fbr in the instance.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        instance = self.bol_instance_id
        if instance:
            vals = {}
            if instance.bol_fulfillment_by == 'FBR':
                fbr_vals = self.prepare_val_for_fbr_configuration()
                vals.update(fbr_vals)
            if instance.bol_fulfillment_by == 'FBB':
                fbb_vals = self.prepare_val_for_fbb_configuration()
                vals.update(fbb_vals)
            if instance.bol_fulfillment_by == 'Both':
                fbr_vals = self.prepare_val_for_fbr_configuration()
                fbb_vals = self.prepare_val_for_fbb_configuration()
                vals.update(fbr_vals)
                vals.update(fbb_vals)
            instance.write(vals)
            company = instance.company_id
            company.set_onboarding_step_done('bol_basic_configuration_onboarding_state')
        return True

    def prepare_val_for_fbr_configuration(self):
        """ Prepare vals for the fbr configuration values.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 1 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        fbr_vals = {}
        fbr_vals.update({'fbr_auto_workflow_id': self.fbr_auto_workflow_id.id,
                         'is_default_sequence_fbr_sales_order': self.is_default_sequence_fbr_sales_order,
                         'fbr_bol_order_prefix': self.fbr_bol_order_prefix,
                         'bol_fbr_warehouse_id': self.bol_fbr_warehouse_id.id,
                         'stock_field': self.bol_instance_stock_field
                         })
        return fbr_vals

    def prepare_val_for_fbb_configuration(self):
        """ Prepare vals for the fbb configuration values.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 1 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        fbb_vals = {}
        fbb_vals.update({'fbb_auto_workflow_id': self.fbb_auto_workflow_id.id,
                         'is_default_sequence_fbb_sales_order': self.is_default_sequence_fbb_sales_order,
                         'fbb_bol_order_prefix': self.fbb_bol_order_prefix,
                         'bol_fbb_warehouse_id': self.bol_fbb_warehouse_id.id,
                         'auto_validate_inventory': self.bol_auto_validate_inventory})
        return fbb_vals

    def bol_fbb_and_fbb_res_config_view_action(self, view_id):
        """ Return the action for open the FBB and FBR configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bol_ept.action_bol_fbr_and_fbb_instance_config")
        action_data = {'view_id': view_id.id, 'views': [(view_id.id, 'form')], 'target': 'new',
                       'name': 'Configurations'}
        instance = self.env['bol.instance.ept'].search_bol_instance()
        if instance:
            action['context'] = {'default_bol_instance_id': instance.id}
        else:
            action['context'] = {}
        action.update(action_data)
        return action

    def bol_general_config_view_action(self, view_id):
        """ Return the action for general configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 30 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bol_ept.action_bol_general_config")
        action_data = {'view_id': view_id.id, 'views': [(view_id.id, 'form')], 'target': 'new',
                       'name': 'Configurations'}
        instance = self.env['bol.instance.ept'].search_bol_instance()
        if instance:
            action['context'] = {'default_bol_instance_id': instance.id}
        else:
            action['context'] = {}
        action.update(action_data)
        return action

    def bol_save_general_configurations(self):
        """ This method is used to set the general configuration of Bol from the Panel.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        instance = self.bol_instance_id
        if instance:
            configuration_vals = self.prepare_vals_for_general_configuration()
            instance.write(configuration_vals)
            company = instance.company_id
            company.set_onboarding_step_done('bol_general_configuration_onboarding_state')

    def prepare_vals_for_general_configuration(self):
        """ This method is use to prepare a vals for the general configuration.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        vals = {}
        vals.update({'bol_auto_create_product': self.bol_auto_create_product,
                     'bol_import_shipment_order_type': self.bol_import_shipment_order_type,
                     'bol_pricelist_id': self.bol_pricelist_id.id,
                     'bol_payment_term_id': self.bol_payment_term_id.id,
                     'bol_team_id': self.bol_team_id.id,
                     'bol_lang_id': self.bol_lang_id.id,
                     'bol_import_order_after_date': self.bol_import_order_after_date,
                     'is_bol_create_schedule': self.is_bol_create_schedule,
                     'bol_activity_type_id': self.bol_activity_type_id.id if self.is_bol_create_schedule else False,
                     'bol_user_ids': [(6, 0, self.bol_user_ids.ids)],
                     'bol_date_deadline': self.bol_date_deadline
                     })
        return vals

    def bol_cron_config_view_action(self, view_id):
        """ Return the action for cron configurations wizard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 20 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bol_ept.action_wizard_bol_cron_configuration_ept")
        action_data = {'view_id': view_id.id, 'views': [(view_id.id, 'form')], 'target': 'new',
                       'name': 'Configurations'}
        instance = self.env['bol.instance.ept'].search_bol_instance()
        if instance:
            action['context'] = {'default_bol_instance_id': instance.id,
                                 'default_bol_fulfillment_by': instance.bol_fulfillment_by,
                                 'is_instance_exists':True}
        else:
            action['context'] = {}
        action['context'].update({'is_calling_from_onboarding_panel': True})
        action.update(action_data)
        return action
