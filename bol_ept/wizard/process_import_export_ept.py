# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
import csv
import logging
from io import StringIO, BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger("Bol Import/Export")

class BolProcessImportExport(models.TransientModel):
    _name = "bol.process.import.export.ept"
    _description = "Bol Import/Export Operations"

    instance_id = fields.Many2one("bol.instance.ept")
    fulfilment_by = fields.Selection([("fbr", "FBR"),
                                      ("fbb", "FBB"),
                                      ("fbr_fbb", "FBR & FBB")], "Operation For")
    fbr_operations = fields.Selection([("import_fbr_order", "Import FBR Orders"),
                                       ("update_order_status", "Update Tracking Informations"),
                                       ("export_stock_from_odoo_to_bol", "Export Stock From Odoo To BOL")],
                                      "FBR Operations")
    fbb_operations = fields.Selection([("import_fbb_order", "Import FBB Orders"),
                                       ("import_fbb_stock", "Import FBB Stock")], "FBB Operations")
    both_operations = fields.Selection([("sync_product", "Sync Products"),
                                        ("import_orders_by_order_ids", "Import Orders - By Order Ids"),
                                        ("import_shipment", "Import Shipments"),
                                        ("import_shipped_order", "Import Shipped Order"),
                                        ("export_prices", "Export Prices to BOL"),
                                        ("map_offers_via_csv", "Map Offers via CSV")], "Operations")

    csv_file = fields.Binary(help="Select CSV file to upload.")
    file_name = fields.Char(help="Name of CSV file.")
    sync_single_offer = fields.Boolean()
    offer_id = fields.Char()
    update_price_in_pricelist = fields.Boolean(string='Update price in Pricelist?', default=False,
                                               help='Update or create product line in pricelist if ticked.')
    auto_create_product = fields.Boolean(string='Auto create product?', default=False,
                                         help='Create product in Odoo if not found.')
    # is_import_shipment_from_api = fields.Boolean(string="Is import shipment of last 3 Months?")
    bol_order_ids = fields.Text(string="Order Ids", help="Based on order reference it will import orders in odoo")
    cron_process_notification = fields.Text(string="Bol.com Note: ", store=False,
                                            help="Used to display that cron will be run after some time")
    is_hide_operation_execute_button = fields.Boolean(default=False, store=False,
                                                      help="Used to hide the execute button from operation wizard "
                                                           "while selected operation cron is running in backend")

    @api.onchange('fulfilment_by')
    def _onchange_fulfilment_by(self):
        """
        Setting other Fulfilment operations to False as the extra options needs to be hidden, when changed to other
        operation
        @author: Maulik Barad on Date 01-Mar-2021.
        """
        if self.fulfilment_by == 'fbr':
            self.fbb_operations = False
            self.both_operations = False
        elif self.fulfilment_by == 'fbb':
            self.fbr_operations = False
            self.both_operations = False
        else:
            self.fbb_operations = False
            self.fbr_operations = False

    @api.onchange("instance_id", "fbr_operations")
    def onchange_bol_fbr_operations(self):
        """
        This method sets field values, when the Instance will be changed.
        """
        instance = self.instance_id
        self.cron_process_notification = False
        self.is_hide_operation_execute_button = False
        if instance:
            if self.fbr_operations == 'import_fbr_order':
                self.bol_check_running_schedulers('ir_cron_import_fbr_open_orders_queue_')
            if self.fbr_operations == 'update_order_status':
                self.bol_check_running_schedulers('ir_cron_update_fbr_order_status_')
            if self.fbr_operations == 'export_stock_from_odoo_to_bol':
                self.bol_check_running_schedulers('ir_cron_export_product_stock_bol_')

    @api.onchange("instance_id", "fbb_operations")
    def onchange_bol_fbb_operations(self):
        instance = self.instance_id
        self.cron_process_notification = False
        self.is_hide_operation_execute_button = False
        if instance:
            if self.fbb_operations == 'import_fbb_order':
                self.bol_check_running_schedulers('ir_cron_import_fbb_open_orders_queue_')

    @api.onchange("instance_id", "both_operations")
    def onchange_bol_both_operations(self):
        instance = self.instance_id
        self.cron_process_notification = False
        self.is_hide_operation_execute_button = False
        if instance:
            if self.both_operations == 'import_shipment':
                self.bol_check_running_schedulers('ir_cron_import_fbr_and_fbb_shipments_')

    def execute(self):
        """
        This method is used to perform various Operations as per selection for a Bol Instance.
        @author: Maulik Barad on Date 01-Mar-2021.
        """
        bol_queue_order_obj = self.env['bol.queue.ept']
        shipped_bol_queue_order_obj = self.env['bol.shipped.data.queue.ept']
        stock_picking_obj = self.env['stock.picking']
        sale_order_obj = self.env['sale.order']
        bol_offer_obj = self.env['bol.offer.ept']
        stock_inventory_obj = self.env['stock.inventory']
        queue_ids = False
        action_name = False
        form_view_name = False
        if self.both_operations == 'map_offers_via_csv':
            self.import_or_map_offers_from_csv()
        if self.both_operations == 'sync_product':
            return self.sync_products()
        if self.fbr_operations == 'import_fbr_order':
            order_queues = bol_queue_order_obj.import_order_queue(self.instance_id, 'FBR')
            if order_queues:
                queue_ids = order_queues
                action_name = "bol_ept.action_bol_order_queue_ept"
                form_view_name = "bol_ept.bol_queue_form_view"

        if self.fbb_operations == 'import_fbb_order':
            order_queues = bol_queue_order_obj.import_order_queue(self.instance_id, 'FBB')
            if order_queues:
                queue_ids = order_queues
                action_name = "bol_ept.action_bol_order_queue_ept"
                form_view_name = "bol_ept.bol_queue_form_view"
        if self.both_operations == 'import_shipped_order':
            is_cron_exist = self.check_running_schedulers(
                    'ir_cron_auto_import_bol_shipped_order_queue_', self.instance_id)
            if not is_cron_exist:
                shipped_bol_queue_order_obj.activate_shipped_order_queue_cron(self.instance_id)
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': _(
                            "Please wait a while Because Shipped order process is take time, Schedular is already "
                            "activated in Backend to Import shipped order for Bol Instance: {}".format(
                                    self.instance_id.name)),
                }
            }
        if self.both_operations == 'import_shipment':
            stock_picking_obj.import_bol_order_shipment(self.instance_id)
        if self.fbr_operations == 'update_order_status':
            sale_order_obj.update_order_status_in_bol(self.instance_id)
        if self.fbr_operations == 'export_stock_from_odoo_to_bol':
            bol_offer_obj.export_product_stock_to_bol(self.instance_id, bol_offer_obj)
        if self.fbb_operations == 'import_fbb_stock':
            stock_inventory_obj.import_fbb_stock_ept(self.instance_id)
        if self.both_operations == 'export_prices':
            bol_offer_obj.export_price_to_bol(self.instance_id, bol_offer_obj)
        if self.both_operations == 'import_orders_by_order_ids':
            self.import_all_bol_orders_by_id()

        if queue_ids and action_name and form_view_name:
            action = self.env.ref(action_name).sudo().read()[0]
            form_view = self.sudo().env.ref(form_view_name)

            if len(queue_ids) == 1:
                action.update({"view_id": (form_view.id, form_view.name), "res_id": queue_ids[0],
                               "views": [(form_view.id, "form")]})
            else:
                action["domain"] = [("id", "in", queue_ids)]
            return action

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def import_all_bol_orders_by_id(self):
        order_ids = self.bol_order_ids.split(',')
        sale_order_obj = self.env['sale.order']
        common_log_book_obj = self.env['common.log.book.ept']
        model_id = self.env['ir.model']._get('sale.order').id
        log_book_vals = {
            'type': 'import',
            'model_id': model_id,
            'res_id': self.id,
            'bol_instance_id': self.instance_id.id,
            'module': 'bol_ept',
            'active': True
        }
        log_book = common_log_book_obj.create(log_book_vals)
        logs = []
        for order in order_ids:
            log_lines = sale_order_obj.import_bol_order_by_id(self.instance_id, order, log_book)
            logs = log_lines + logs
        log_book.write({'log_lines': log_lines})

    def bol_selective_offers_stock_export(self):
        """
        This method export stock of particular selected products in list view or from form view's action menu.
        @author: Ekta bhut
        """
        bol_offer_obj = self.env['bol.offer.ept']
        bol_offer_ids = self._context.get('active_ids')

        bol_instances = self.env['bol.instance.ept'].search([])
        for instance in bol_instances:
            bol_offers = bol_offer_obj.search([('bol_instance_id', '=', instance.id), ('exported_in_bol', '=', True),
                                               ('id', 'in', bol_offer_ids), ('fulfillment_by', '=', 'FBR')])
            bol_offer_obj.export_product_stock_to_bol(instance, bol_offers)
        return True

    def bol_selective_offers_price_export(self):
        """
        This method export stock of particular selected products in list view or from form view's action menu.
        @author: Ekta bhut
        """
        bol_offer_obj = self.env['bol.offer.ept']
        bol_offer_ids = self._context.get('active_ids')

        bol_instances = self.env['bol.instance.ept'].search([])
        for instance in bol_instances:
            bol_offers = bol_offer_obj.search([('bol_instance_id', '=', instance.id), ('exported_in_bol', '=', True),
                                               ('id', 'in', bol_offer_ids)])
            bol_offer_obj.export_price_to_bol(instance, bol_offers)
        return True

    def sync_products(self):
        """
        This method is used to sync product from Bol.com
        :return:
        """
        bol_offer_obj = self.env['bol.offer.ept']
        if not self.sync_single_offer:
            return bol_offer_obj.create_sync_active_products(self.instance_id,
                                                             self.update_price_in_pricelist,
                                                             self.auto_create_product)

        common_log_line_obj = self.env['common.log.lines.ept']
        model_id = common_log_line_obj.get_model_id("bol.product.sync.ept")
        log_rec = self.create_import_log(model_id, self.instance_id)

        bol_offer_obj.sync_product(self.instance_id, log_rec, product_offerid=self.offer_id,
                                   update_price=self.update_price_in_pricelist,
                                   auto_create_product=self.auto_create_product)
        return True

    def import_or_map_offers_from_csv(self):
        """
        This method used to import product using csv file in shopify third layer.
        @author: Maulik Barad on Date 12-Oct-2020.
        """
        common_log_obj = self.env["common.log.book.ept"]
        common_log_line_obj = self.env["common.log.lines.ept"]
        model_id = common_log_line_obj.get_model_id("bol.process.import.export.ept")

        if not self.file_name.endswith(".csv"):
            raise UserError(_("Please Provide Only .csv File To Import Product !!!"))

        instance = self.instance_id
        log_book_id = common_log_obj.create({"type": "import",
                                             "module": "bol_ept",
                                             "bol_instance_id": instance.id if instance else False,
                                             "model_id": model_id})
        file_data = self.read_file()
        self.validate_required_csv_header(file_data)
        # Title,Internal Reference,Seller SKU,Fulfillment
        for record in file_data:
            if not (record["Title"] or record["Internal Reference"] or record["Seller SKU"] or record["Fulfillment"]):
                message = "PRODUCT_ID or Product name or SKU for Bol Offer is not found for Product - %s" % record[
                    "product_name"]
                common_log_line_obj.bol_create_order_log_line(message, model_id, False, log_book_id)
                continue

            self.create_or_update_bol_offer_from_csv(instance, record)

        if not log_book_id.log_lines:
            log_book_id.unlink()
        return True

    def read_file(self):
        """
        This method reads CSV file.
        """
        import_file = BytesIO(base64.decodebytes(self.csv_file))
        file_read = StringIO(import_file.read().decode())
        reader = csv.DictReader(file_read, delimiter=",")

        return reader

    def validate_required_csv_header(self, file_data):
        """
        This method is used to validate required csv header while csv file import for products.
        """
        required_fields = ["Title", "Internal Reference", "Seller SKU", "Fulfillment", ]

        for required_field in required_fields:
            if required_field not in file_data.fieldnames:
                raise UserError(_("Required column is not available in File."))

    def create_or_update_bol_offer_from_csv(self, instance, offer_data):
        """
        This method is used to create or update the product from the CSV file.
        @return:
        """
        bol_offer_obj = self.env['bol.offer.ept']
        product_obj = self.env['product.product']
        # ["Title", "Internal Reference", "Seller SKU", "Fulfillment",]
        odoo_sku = offer_data.get('Internal Reference')
        name = offer_data.get('Title')
        product = product_obj.search([('default_code', '=', odoo_sku)], limit=1)
        if product:
            vals = {'bol_instance_id': instance.id, 'odoo_product_id': product.id,
                    'name': name, 'fulfillment_by': offer_data.get("Fulfillment"),
                    'reference_code': offer_data.get("Seller SKU"),
                    'bol_bsku': offer_data.get("Seller SKU"),
                    'ean_product': offer_data.get('EAN'), 'is_publish': True,
                    'exported_in_bol': True}
            bol_offer = bol_offer_obj.search([('bol_instance_id', '=', instance.id),
                                              ('odoo_product_id', '=', product.id),
                                              ('reference_code', '=', offer_data.get("Seller SKU")),
                                              ('fulfillment_by', '=', offer_data.get('Fulfillment'))], limit=1)

            if bol_offer:
                _logger.info("Updating Bol offer - %s" % name)
                bol_offer.write(vals)
            else:
                _logger.info("Creating Bol offer - %s" % name)
                bol_offer_obj.create(vals)

        return True

    def create_import_log(self, model_id, instance_id):
        """
        This method is used to create import log
        :param model_id: model id
        :param instance_id: bol instance id
        :return: log record
        """
        log_book_obj = self.env['common.log.book.ept']
        log_vals = {
            'active': True, 'type': 'import',
            'model_id': model_id, 'bol_instance_id': instance_id.id,
            'res_id': self.id, 'module': 'bol_ept'
        }
        log_rec = log_book_obj.create(log_vals)
        return log_rec

    def check_running_schedulers(self, cron_xml_id, instance_id):
        """
        use: 1. If scheduler is running for ron_xml_id + seller_id, then this function will
        notify user that the process they are doing will be running in the scheduler.
        if they will do this process then the result cause duplicate.
        2. Also if scheduler is in progress in backend then the execution will give UserError
           Popup and terminates the process until scheduler job is done.
        :param instance_id:
        :param cron_xml_id: string[cron xml id]
        :return:
        """
        cron_id = self.env.ref('bol_ept.%s%d' % (cron_xml_id, instance_id.id),
                               raise_if_not_found=False)
        if cron_id and cron_id.sudo().active:
            res = cron_id.sudo().try_cron_lock()
            if self._context.get('raise_warning') and res and res.get('reason'):
                raise Warning(_("You are not allowed to run this Action. \n"
                                "The Scheduler is already started the Process of Importing "
                                "Orders."))

    def download_sample_attachment(self):
        """
        This Method relocates download sample file of amazon.
        :return: This Method return file download file.
        """
        attachment = self.env['ir.attachment'].search([('name', '=', 'import_bol_product_sample.csv')])
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachment.id),
            'target': 'new',
            'nodestroy': False,
        }

    def bol_check_running_schedulers(self, cron_xml_id):
        """ This method is used to check that selected operation cron is running or not.
            :param cron_xml_id: Xml id of the scheduler action.
            @author: Ekta Bhut
        """
        try:
            cron_id = self.env.ref('bol_ept.%s%d' % (cron_xml_id, self.instance_id.id))
        except:
            return
        if cron_id and cron_id.sudo().active:
            res = cron_id.try_cron_lock()
            if res == None:
                res = {}
            if res and res.get('reason') or res.get('result') == 0:
                message = "You are not allowed to run this process.The Scheduler is already started the Process."
                self.cron_process_notification = message
                self.is_hide_operation_execute_button = True
            if res and res.get('result'):
                self.cron_process_notification = "This process is also performed by a scheduler, and the next " \
                                                 "schedule for this process will run in %s minutes." % res.get('result')
            elif res and res.get('reason'):
                self.cron_process_notification = res.get('reason')
