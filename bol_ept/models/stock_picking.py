# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time
from datetime import datetime

from odoo import models, fields, api

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bol_shipment_id = fields.Char("Bol Shipment ID")
    bol_fulfillment_by = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB')], 'fulfilment Method',
                                          readonly=True)
    bol_instance_id = fields.Many2one('bol.instance.ept', "Instance")
    updated_in_bol = fields.Boolean(default=False)
    canceled_in_bol = fields.Boolean(default=False)
    is_bol_delivery_order = fields.Boolean('Bol Delivery Order')
    bol_trasport_id = fields.Char("Bol Transport ID")
    bol_process_status_id = fields.Char("Bol Process Status ID")
    process_status = fields.Selection([('PENDING', 'PENDING'),
                                       ('FAILURE', 'FAILURE'),
                                       ('TIMEOUT', 'TIMEOUT'),
                                       ('SUCCESS', 'SUCCESS')])

    def import_bol_order_shipment(self, instance):
        """
        Import Bol order shipment.
        :param instance: Bol Instance
        :return:
        """
        fulfillment_by = instance.get_bol_instance_fulfillment_by()
        warehouse_ids = instance.get_bol_warehouse_ids()
        order_ids = self.get_bol_order_ids(instance, warehouse_ids, fulfillment_by)
        is_mrp_installed = self._check_mrp_module_install()
        #order_ids = self.env['sale.order'].browse(586)
        count = 0
        for order in order_ids:
            count += 1
            if count == 10:
                count = 0
                self._cr.commit()
            bol_order_id = order.bol_order_id
            shipment_response = self.get_single_shipment_order_response(instance, bol_order_id)
            for shipment in shipment_response.get('shipments', []):
                shipment_id = str(shipment.get('shipmentId'))
                shipment_full_response = order.get_single_order_shipment_response(instance, shipment_id)
                if shipment_full_response:
                    _logger.info("Order is processing {0}".format(order.bol_order_id))
                    if order.state == 'draft':
                        order.action_confirm()
                    picking_ids = order.picking_ids.filtered(lambda l: l.state not in ['done', 'cancel'])
                    if not picking_ids:
                        _logger.info("Order can not be possible because delivery order is not found")
                        continue
                    if picking_ids:
                        self.update_picking_bol_vals(instance, picking_ids, shipment_full_response)
                        self.process_bol_order_picking(order, picking_ids, shipment_full_response, is_mrp_installed)

        return True

    def update_picking_bol_vals(self, instance, picking_ids, shipment_full_response):
        """
        Update Bol Picking values
        :param instance: Bol Instance
        :param picking_ids: Picking Ids
        :param shipment_full_response: Shipement response
        :return:
        """
        picking_vals = {}
        carrier_id = False
        shipment_id = shipment_full_response.get('shipmentId')
        if not picking_ids.bol_shipment_id or not picking_ids.carrier_id:
            picking_vals.update({'bol_shipment_id': shipment_id, 'date_done': datetime.now()})
        transport_code = shipment_full_response.get('transport', {}).get('transporterCode', '')
        if transport_code:
            carrier_id = self.get_shipping_method_bol_ept( \
                    transport_code, instance.shipment_charge_product_id)
        if carrier_id:
            picking_vals.update({'carrier_id': carrier_id})
        if shipment_full_response.get('transport', {}).get('trackAndTrace', ''):
            tracking_no = shipment_full_response.get('transport', {}).get('trackAndTrace', '')
            picking_vals.update({'carrier_tracking_ref': tracking_no})
        if picking_vals:
            picking_ids.write(picking_vals)

    def get_shipping_method_bol_ept(self, code, ship_product):
        """
        Get Bol shipping method
        :param code: shipping code
        :param ship_product: shipping product
        :return: Delivery carrier ID
        @author : Ekta Bhut
        """
        delivery_carrier_obj = self.env['delivery.carrier']
        bol_delivery_carrier_obj = self.env['bol.delivery.carrier.code.ept']

        carrier_id = delivery_carrier_obj.search([('bol_delivery_carrier_code_id.code', '=', code)], limit=1)
        if carrier_id:
            return carrier_id.id
        carrier_code = bol_delivery_carrier_obj.create({'name': code,
                                                        'code': code})
        carrier_id = delivery_carrier_obj.create({
            'name': code,
            'product_id': ship_product.id,
            'bol_delivery_carrier_code_id': carrier_code.id})
        return carrier_id.id

    def _check_mrp_module_install(self):
        module_obj = self.env['ir.module.module']
        mrp_module = module_obj.sudo().search([('name', '=', 'mrp'), ('state', '=', 'installed')])
        return True if mrp_module else False

    def get_bol_order_ids(self, instance, warehouse_ids, fulfillment_by):
        """
        Get bol order for process shipment for import shipment.
        :param instance: Bol Instance
        :param warehouse_ids: Warehouse IDs
        :param fulfillment_by: FBB or FBR
        :return:
        @author : Ekta Bhut
        """
        order_ids = []
        picking_ids = self.search([('bol_instance_id', '=', instance.id),
                                   ('bol_fulfillment_by', 'in', fulfillment_by),
                                   ('updated_in_bol', '=', False),
                                   ('picking_type_id.warehouse_id', 'in', warehouse_ids.ids),
                                   ('backorder_id', '=', False),
                                   ('state', 'in', ['confirmed', 'assigned']),
                                   ('picking_type_id.code', '=', 'outgoing'), ])
        order_ids = picking_ids.mapped('sale_id') if picking_ids else []

        return order_ids

    def get_single_shipment_order_response(self, instance, order_id):
        """
        This method is used to get single shipment response.
        :param instance: Bol Instance
        :param order_id: Order ID
        :return:
        @author : Ekta Bhut
        """
        order_id = 'order-id=%s' % order_id
        response_obj, shipment_response = BolAPI.get('shipment_list', instance.bol_auth_token, order_id)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, shipment_response = BolAPI.get('shipment_list', instance.bol_auth_token,
                                                         order_id)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, shipment_response = BolAPI.get('shipment_list', instance.bol_auth_token,
                                                         order_id)
        if response_obj.status_code == 404:
            _logger.info("Shipment %s NOT FOUND SO SKIP IT" % order_id)
            return {}
        return shipment_response

    def process_bol_order_picking(self, order, picking, shipment_response, is_mrp_installed):
        """
        This method is used to process bol order picking while import shipments
        :param order: Order
        :param picking: Picking
        :param shipment_response: Shipment response
        :param is_mrp_installed: True or False
        :return:
        @author : Ekta Bhut
        """
        sale_order_obj = self.env['sale.order']
        skip_sms = {"skip_sms": True}
        shipment_lines = shipment_response.get('shipmentItems')
        for shipment_line in shipment_lines:
            bom_lines = []
            bol_order_line_id = shipment_line.get('orderItemId')
            done_qty = shipment_line.get('quantity')
            order_line = order.order_line.filtered(lambda l: l.bol_order_item_id == bol_order_line_id)
            if is_mrp_installed:
                bom_lines = sale_order_obj.check_for_bom_product(order_line.product_id)
            if bom_lines:
                for bom_line in bom_lines:
                    product = bom_line[0].product_id
                    product_qty = bom_line[1].get('qty', 0) * done_qty
                    picking.move_lines.filtered(lambda l: l.sale_line_id.id == order_line.id and l.product_id.id
                                                          == product.id)
                    self.set_done_qty_in_bol_stock_move(order_line, stock_move, product_qty)
            else:
                stock_move = picking.move_lines.filtered(lambda l: l.sale_line_id.id == order_line.id)
                self.set_done_qty_in_bol_stock_move(order_line, stock_move, done_qty)
        result = picking.with_context(**skip_sms).button_validate()
        if isinstance(result, dict):
            dict(result.get("context")).update(skip_sms)
            context = result.get("context")  # Merging dictionaries.
            model = result.get("res_model", "")
            # model can be stock.immediate.transfer or stock backorder.confirmation
            if model:
                record = self.env[model].with_context(context).create({})
                record.process()
        if picking.state == "done":
            picking.updated_in_bol = True

    def set_done_qty_in_bol_stock_move(self, order_line, stock_move, done_qty):
        """
        Set done quantity in Bol.com
        :param done_qty: Quantity
        :param order_line: Order line
        :param stock_move: Stock move
        :return:
        @author : Ekta Bhut
        """
        stock_move._set_quantity_done(float(done_qty))

    @api.model
    def auto_import_fbr_fbb_shipments(self, ctx={}):
        """
        This method is called from Schedular
        :param ctx: Argument
        :return:
        @author : Ekta Bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = ctx.get('bol_instance_id')
        if instance_id:
            instance = bol_instance_obj.browse(instance_id)
            self.import_bol_order_shipment(instance)
