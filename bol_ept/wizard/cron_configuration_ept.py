# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

class BolCronConfigurationEpt(models.TransientModel):
    _name = 'bol.cron.configuration.ept'
    _description = "Bol Cron Configuration"

    def _get_bol_instance(self):
        return self.env.context.get('bol_instance_id', False)

    def _get_bol_fulfillment_by(self):
        return self.env.context.get('bol_fulfillment_by', False)

    bol_instance_id = fields.Many2one('bol.instance.ept', string='Bol Instance', default=_get_bol_instance,
                                      help="Bol Instance")
    bol_fulfillment_by = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB'), ('Both', 'FBR & FBB')],
                                          string='Fulfilment By', default=_get_bol_fulfillment_by)

    # Auto Import FBR orders
    bol_auto_import_fbr_order = fields.Boolean(string='Auto Request FBR Order ?')
    bol_order_next_execution = fields.Datetime('Import FBR Order Next Execution',
                                               help='Next execution time')
    bol_order_import_interval_number = fields.Integer(
            'Import FBR Order Interval Number', help="Repeat every x.")
    bol_order_import_interval_type = fields.Selection([('hours', 'Hours'),
                                                       ('days', 'Days'),
                                                       ('minutes', 'Minutes')], 'Import FBR Order '
                                                                                'Interval Unit')
    bol_order_import_user_id = fields.Many2one("res.users",
                                               string="Import FBR Order User")
    # Export FBR stock
    bol_auto_export_stock = fields.Boolean(string='Auto Export Stock ?')
    export_stock_next_execution = fields.Datetime('Export Stock Next Execution',
                                                  help='Next execution time')
    export_stock_interval_number = fields.Integer(
            'Export Stock Interval Number', help="Repeat every x.")
    export_stock_interval_type = fields.Selection([('hours', 'Hours'),
                                                   ('days', 'Days')],
                                                  'Export Stock Interval Unit')
    export_stock_user_id = fields.Many2one("res.users",
                                           string="Export Stock User")
    # Update order status FBR
    bol_auto_update_order_status = fields.Boolean(string='Auto Update FBR Order Status ?')
    update_status_next_execution = fields.Datetime('Update Order Status Next Execution',
                                                   help='Next execution time')
    update_status_interval_number = fields.Integer(
            'Update Order Status Interval Number', help="Repeat every x.")
    update_status_interval_type = fields.Selection([('hours', 'Hours'),
                                                    ('days', 'Days')],
                                                   'Update Order Status Interval Unit')
    update_status_user_id = fields.Many2one("res.users",
                                            string="Update FBR Order User")
    # Import FBB open orders
    bol_auto_import_fbb_order = fields.Boolean( \
            string='Auto Request FBB Order ?')
    bol_fbb_order_next_execution = fields.Datetime('Import FBB Order Next Execution',
                                                   help='Next execution time')
    bol_fbb_order_import_interval_number = fields.Integer( \
            'Import FBB Order Interval Number', help="Repeat every x.")
    bol_fbb_order_import_interval_type = fields.Selection([('hours', 'Hours'),
                                                           ('days', 'Days'),
                                                           ('minutes', 'Minutes')], 'Import FBB Order Interval Unit')
    bol_fbb_order_import_user_id = fields.Many2one("res.users",
                                                   string="Import FBB Order User")
    # Import Shipment for FBB & FBR
    auto_import_process_bol_shipment = fields.Boolean(string='Auto Import & Process BOL Shipment')
    import_process_shipment_next_execution = fields.Datetime('Auto Process Shipment Next Execution',
                                                             help='Next execution time')
    import_process_shipment_interval_number = fields.Integer( \
            'Process Shipment Interval Number', help="Repeat every x.")
    import_process_shipment_interval_type = fields.Selection([('hours', 'Hours'),
                                                              ('days', 'Days'),
                                                              ('minutes', 'Minutes')],
                                                             'Process Shipment Interval Unit')
    import_process_shipment_user_id = fields.Many2one("res.users", string="Process Shipment User")

    @api.constrains("bol_order_import_interval_number","export_stock_interval_number","update_status_interval_number",
                    "bol_fbb_order_import_interval_number","import_process_shipment_interval_number")
    def check_interval_time(self):
        """
        It does not let set the cron execution time to Zero.
        @author: Maulik Barad on Date 03-Dec-2020.
        """
        for record in self:
            is_zero = False
            if record.bol_auto_import_fbr_order and record.bol_order_import_interval_number <= 0:
                is_zero = True
            if record.bol_auto_export_stock and record.export_stock_interval_number <= 0:
                is_zero = True
            if record.bol_auto_update_order_status and record.update_status_interval_number <= 0:
                is_zero = True
            if record.bol_auto_import_fbb_order and record.bol_fbb_order_import_interval_number <= 0:
                is_zero = True
            if record.auto_import_process_bol_shipment and record.import_process_shipment_interval_number <= 0:
                is_zero = True
            if is_zero:
                raise ValidationError(_("Cron Execution Time can't be set to 0(Zero). "))

    @api.onchange("bol_instance_id")
    def onchange_bol_instance_id(self):
        """
        Set cron field value while open the wizard for cron configuration from the instance form view.
        s Pvt. Ltd on date 16/11/2019.
        Task Id : 157716
        """
        instance = self.bol_instance_id
        self.update_fbr_order_import_cron_field(instance)
        self.update_fbr_stock_export_cron_field(instance)
        self.update_fbr_update_order_status_cron_field(instance)
        self.update_fbb_order_import_cron_field(instance)
        self.update_import_shipment_cron_field(instance)

    def update_fbr_order_import_cron_field(self, instance):
        """
        Set Order import fields value while open the wizard for cron configuration from the instance form view.
        """
        try:
            fbr_order_import_cron_exist = instance and self.env.ref(
                    'bol_ept.ir_cron_import_fbr_open_orders_queue_%d' % instance.id)
        except:
            fbr_order_import_cron_exist = False
        if fbr_order_import_cron_exist:
            self.bol_auto_import_fbr_order = fbr_order_import_cron_exist.active or False
            self.bol_order_import_interval_number = fbr_order_import_cron_exist.interval_number or False
            self.bol_order_import_interval_type = fbr_order_import_cron_exist.interval_type or False
            self.bol_order_next_execution = fbr_order_import_cron_exist.nextcall or False
            self.bol_order_import_user_id = fbr_order_import_cron_exist.user_id.id or False

    def update_fbr_stock_export_cron_field(self, instance):
        """
        Set Order import fields value while open the wizard for cron configuration from the instance form view.
        """
        try:
            export_fbr_stock_cron = instance and self.env.ref(
                    'bol_ept.ir_cron_export_product_stock_bol_%d' % instance.id)
        except:
            export_fbr_stock_cron = False
        if export_fbr_stock_cron:
            self.bol_auto_export_stock = export_fbr_stock_cron.active or False
            self.export_stock_interval_number = export_fbr_stock_cron.interval_number or False
            self.export_stock_interval_type = export_fbr_stock_cron.interval_type or False
            self.export_stock_next_execution = export_fbr_stock_cron.nextcall or False
            self.export_stock_user_id = export_fbr_stock_cron.user_id.id or False

    def update_fbr_update_order_status_cron_field(self, instance):
        """
        Set Order import fields value while open the wizard for cron configuration from the instance form view.
        """
        try:
            update_fbr_order_status = instance and self.env.ref(
                    'bol_ept.ir_cron_update_fbr_order_status_%d' % instance.id)
        except:
            update_fbr_order_status = False
        if update_fbr_order_status:
            self.bol_auto_update_order_status = update_fbr_order_status.active or False
            self.update_status_interval_number = update_fbr_order_status.interval_number or False
            self.update_status_interval_type = update_fbr_order_status.interval_type or False
            self.update_status_next_execution = update_fbr_order_status.nextcall or False
            self.update_status_user_id = update_fbr_order_status.user_id.id or False

    def update_fbb_order_import_cron_field(self, instance):
        """
        Set Order import fields value while open the wizard for cron configuration from the instance form view.
        """
        try:
            fbb_order_import_cron = instance and self.env.ref(
                    'bol_ept.ir_cron_import_fbb_open_orders_queue_%d' % instance.id)
        except:
            fbb_order_import_cron = False
        if fbb_order_import_cron:
            self.bol_auto_import_fbb_order = fbb_order_import_cron.active or False
            self.bol_fbb_order_import_interval_number = fbb_order_import_cron.interval_number or False
            self.bol_fbb_order_import_interval_type = fbb_order_import_cron.interval_type or False
            self.bol_fbb_order_next_execution = fbb_order_import_cron.nextcall or False
            self.bol_fbb_order_import_user_id = fbb_order_import_cron.user_id.id or False

    def update_import_shipment_cron_field(self, instance):
        """
        Set Order import fields value while open the wizard for cron configuration from the instance form view.
        """
        try:
            import_shipment_cron = instance and self.env.ref(
                    'bol_ept.ir_cron_import_fbr_and_fbb_shipments_%d' % instance.id)
        except:
            import_shipment_cron = False
        if import_shipment_cron:
            self.auto_import_process_bol_shipment = import_shipment_cron.active or False
            self.import_process_shipment_interval_number = import_shipment_cron.interval_number or False
            self.import_process_shipment_interval_type = import_shipment_cron.interval_type or False
            self.import_process_shipment_next_execution = import_shipment_cron.nextcall or False
            self.import_process_shipment_user_id = import_shipment_cron.user_id.id or False

    def setup_fbr_schedular(self):
        instance = self.bol_instance_id
        self.setup_bol_fbr_order_import_cron(instance)
        self.setup_bol_fbr_order_status_update_cron(instance)
        self.setup_bol_export_product_stock_cron(instance)

    def setup_both_schedular(self):
        instance = self.bol_instance_id
        self.setup_bol_import_shipment_cron(instance)

    def setup_fbb_schedulars(self):
        instance = self.bol_instance_id
        self.setup_bol_fbb_order_import_cron(instance)

        return True

    def prepare_val_for_cron(self, instance,interval_number, interval_type, user_id):
        """ This method is used to prepare a vals for the cron configuration.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 24 October 2020 .
            Task_id: 167537
        """
        vals = {'active': True,
                'interval_number': interval_number,
                'interval_type': interval_type,
                'user_id': user_id.id if user_id else False,
                'bol_instance_cron_id' : instance.id}
        return vals

    def create_ir_module_data(self, name, new_cron):
        """ This method is used to create a record of ir model data
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 26 October 2020 .
            Task_id: 167537 - Code refactoring
        """
        self.env['ir.model.data'].create({'module': 'bol_ept',
                                          'name': name,
                                          'model': 'ir.cron',
                                          'res_id': new_cron.id,
                                          'noupdate': True})

    def check_core_bol_cron(self, name):
        """
        This method will check for the core cron and if doesn't exist, then raise error.
        @author: Maulik Barad on Date 28-Sep-2020.
        @param name: Name of the core cron.
        """
        try:
            core_cron = self.env.ref(name)
        except:
            core_cron = False

        if not core_cron:
            raise UserError(
                    _('Core settings of Shopify are deleted, please upgrade Shopify module to back this settings.'))
        return core_cron

    def setup_bol_fbr_order_import_cron(self, instance):
        """
        This method is used to setup the inventory export cron.
        """
        try:
            cron_exist = self.env.ref('bol_ept.ir_cron_import_fbr_open_orders_queue_%d' % instance.id)
        except:
            cron_exist = False
        if self.bol_auto_import_fbr_order:
            nextcall = datetime.now() + _intervalTypes[self.bol_order_import_interval_type](
                    self.bol_order_import_interval_number)
            vals = self.prepare_val_for_cron(instance,self.bol_order_import_interval_number,
                                             self.bol_order_import_interval_type,
                                             self.bol_order_import_user_id)
            vals.update({'nextcall': self.bol_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.auto_import_fbr_open_order_queue(ctx={'bol_instance_id':%d})" % instance.id,
                         })

            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_bol_cron("bol_ept.ir_cron_import_fbr_open_orders_queue")

                name = instance.name + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_import_fbr_open_orders_queue_%d' % (instance.id)
                self.create_ir_module_data(name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_bol_fbr_order_status_update_cron(self, instance):
        """
        This method is used to setup the inventory export cron.
        """
        try:
            cron_exist = self.env.ref('bol_ept.ir_cron_update_fbr_order_status_%d' % instance.id)
        except:
            cron_exist = False
        if self.bol_auto_import_fbr_order:
            nextcall = datetime.now() + _intervalTypes[self.bol_order_import_interval_type](
                    self.bol_order_import_interval_number)
            vals = self.prepare_val_for_cron(instance,self.bol_order_import_interval_number,
                                             self.bol_order_import_interval_type,
                                             self.bol_order_import_user_id)
            vals.update({'nextcall': self.bol_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.auto_update_fbr_order_status(ctx={'bol_instance_id':%d})" % instance.id,
                         })

            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_bol_cron("bol_ept.ir_cron_update_fbr_order_status")

                name = instance.name + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_update_fbr_order_status_%d' % instance.id
                self.create_ir_module_data(name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_bol_export_product_stock_cron(self, instance):
        """
        This method is used to setup the inventory export cron.
        """
        try:
            cron_exist = self.env.ref('bol_ept.ir_cron_export_product_stock_bol_%d' % instance.id)
        except:
            cron_exist = False
        if self.bol_auto_export_stock:
            nextcall = datetime.now() + _intervalTypes[self.export_stock_interval_type](
                    self.export_stock_interval_number)
            vals = self.prepare_val_for_cron(instance,self.export_stock_interval_number,
                                             self.export_stock_interval_type,
                                             self.export_stock_user_id)
            vals.update({'nextcall': self.bol_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.auto_update_fbr_product_stock(ctx={'bol_instance_id':%d})" % instance.id,
                         })

            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_bol_cron("bol_ept.ir_cron_export_product_stock_bol")

                name = instance.name + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_export_product_stock_bol_%d' % instance.id
                self.create_ir_module_data(name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_bol_fbb_order_import_cron(self, instance):
        """
        This method is used to setup the inventory export cron.
        """
        try:
            cron_exist = self.env.ref('bol_ept.ir_cron_import_fbb_open_orders_queue_%d' % instance.id)
        except:
            cron_exist = False
        if self.bol_auto_import_fbb_order:
            nextcall = datetime.now() + _intervalTypes[self.bol_fbb_order_import_interval_type](
                    self.bol_fbb_order_import_interval_number)
            vals = self.prepare_val_for_cron(instance,self.bol_fbb_order_import_interval_number,
                                             self.bol_fbb_order_import_interval_type,
                                             self.bol_fbb_order_import_user_id)
            vals.update({'nextcall': self.bol_fbb_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.auto_import_fbb_open_order_queue(ctx={'bol_instance_id':%d})" % instance.id,
                         })

            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_bol_cron("bol_ept.ir_cron_import_fbb_open_orders_queue")

                name = instance.name + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_import_fbb_open_orders_queue_%d' % instance.id
                self.create_ir_module_data(name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_bol_import_shipment_cron(self, instance):
        """
        This method is used to setup the inventory export cron.
        """
        try:
            cron_exist = self.env.ref('bol_ept.ir_cron_import_fbr_and_fbb_shipments_%d' % instance.id)
        except:
            cron_exist = False
        if self.auto_import_process_bol_shipment:
            nextcall = datetime.now() + _intervalTypes[self.import_process_shipment_interval_type](
                    self.import_process_shipment_interval_number)
            vals = self.prepare_val_for_cron(instance,self.import_process_shipment_interval_number,
                                             self.import_process_shipment_interval_type,
                                             self.import_process_shipment_user_id)
            vals.update({'nextcall': self.import_process_shipment_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.auto_import_fbr_fbb_shipments(ctx={'bol_instance_id':%d})" % instance.id,
                         })

            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_bol_cron("bol_ept.ir_cron_import_fbr_and_fbb_shipments")

                name = instance.name + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_import_fbr_and_fbb_shipments_%d' % instance.id
                self.create_ir_module_data(name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def save_bol_cron_configuration(self):
        """ This method is used to save cron job fields value.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 21 July 2021 .
            Task_id: 175221 - BOl.com panel
        """
        instance = self.bol_instance_id
        if instance:
            self.setup_bol_import_shipment_cron(instance)
            if self.bol_fulfillment_by == 'Both':
                self.setup_bol_fbb_order_import_cron(instance)
                self.setup_bol_fbr_order_import_cron(instance)
                self.setup_bol_fbr_order_status_update_cron(instance)
                self.setup_bol_export_product_stock_cron(instance)
            elif self.bol_fulfillment_by == 'FBR':
                self.setup_bol_fbr_order_import_cron(instance)
                self.setup_bol_fbr_order_status_update_cron(instance)
                self.setup_bol_export_product_stock_cron(instance)
            else:
                self.setup_bol_fbb_order_import_cron(instance)
            if self._context.get('is_calling_from_onboarding_panel', False):
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "bol_ept.bol_onboarding_confirmation_wizard_action")
                action['context'] = {'bol_instance_id': instance.id}
                return action
            return {'type': 'ir.actions.client', 'tag': 'reload'}
