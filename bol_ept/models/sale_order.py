# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import logging
import time
from datetime import datetime

import pytz
from dateutil import parser
from odoo import models, fields, api

from ..bol_api.bol_api import BolAPI

utc = pytz.utc
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_bol_order_status(self):
        """
        Get Bol Order Status based on the Picking.
        """
        for order in self:
            if order.bol_instance_id:
                pickings = order.picking_ids.filtered(lambda x: x.state != "cancel")
                if pickings:
                    outgoing_picking = pickings.filtered(
                            lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("updated_in_bol")):
                        order.updated_in_bol = True
                        continue
                if order.state != 'draft' and order.moves_count > 0:
                    move_ids = self.env["stock.move"].search([("picking_id", "=", False),
                                                              ("sale_line_id", "in", order.order_line.ids)])
                    state = set(move_ids.mapped('state'))
                    if len(set(state)) == 1 and 'done' in set(state):
                        order.updated_in_bol = True
                        continue
                order.updated_in_bol = False
                continue
            order.updated_in_bol = False

    def _search_bol_order_ids(self, operator, value):
        query = """select so.id from stock_picking sp
                    inner join sale_order so on so.procurement_group_id=sp.group_id                   
                    inner join stock_location on stock_location.id=sp.location_dest_id and stock_location.usage='customer'
                    where sp.updated_in_bol %s true and sp.state != 'cancel'
                    """ % (operator)
        if operator == '=':
            query += """union all
                    select so.id from sale_order as so
                    inner join sale_order_line as sl on sl.order_id = so.id
                    inner join stock_move as sm on sm.sale_line_id = sl.id
                    where sm.picking_id is NULL and sm.state = 'done' and so.bol_instance_id notnull"""
        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id', 'in', order_ids)]

    bol_instance_id = fields.Many2one('bol.instance.ept', string="Bol Instance", copy=False)
    bol_order_number = fields.Char(string="Bol Order Number", copy=False)
    updated_in_bol = fields.Boolean(compute="_get_bol_order_status", search="_search_bol_order_ids")
    bol_order_id = fields.Char(string="Bol Order ID", copy=False)
    bol_fulfillment_by = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB')], default='FBR', copy=False)

    _sql_constraints = [('unique_bol_order',
                         'unique(bol_instance_id,bol_order_number,bol_fulfillment_by)',
                         "Bol order must be Unique.")]

    # Following methods are there for Process bol open orders
    def process_bol_open_order_queue_line(self, instance, queue_line, fulfillment_by, log_rec):
        """
        This method is used to Process bol open order queue line.
        :param instance: Bol Instance
        :param fulfillment_by: FBB or FBR
        :param queue_line: Queue line
        :param log_rec: Common log book record
        :return:
        """
        log_lines = []
        order_queue_data = json.loads(queue_line.bol_order_data)
        order_data_temp = []
        count = 0
        for order_data in order_queue_data:
            logs = []
            count = count + 1
            if count == 10:
                count = 0
                self._cr.commit()
            bol_order_id = order_data.get('orderId')
            date_order = order_data.get('orderPlacedDateTime')
            date_order = parser.parse(date_order).astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
            order_date = datetime.strptime(date_order, '%Y-%m-%d %H:%M:%S')
            if instance.bol_import_order_after_date > order_date:
                message = "Order %s is not imported because it is created before %s, Creation time: %s" % (
                    bol_order_id, instance.bol_import_order_after_date, order_date)
                vals = {'message': message, 'log_book_id': log_rec.id, 'bol_order_data_queue_line_id':
                    queue_line.id, 'order_ref': bol_order_id}
                log_lines.append([0, 0, vals])
                _logger.info(message)
                continue
            is_order_exist = self.search_bol_order_exist_or_not(instance, bol_order_id,
                                                                fulfillment_by)
            if is_order_exist:
                order_data_temp.append(order_data)
                continue
            else:

                order_response = self.get_single_order_response(instance, bol_order_id)
                if order_response:
                    order, logs = self.create_bol_order_ept(instance, queue_line, fulfillment_by,
                                                            order_response, log_rec)
                    if order:
                        order_data_temp.append(order_data)
                        order.process_orders_and_invoices_ept()
                    self._cr.commit()
                else:
                    message = "Order can not be found with open order API %s" % bol_order_id
                    vals = {'message': message, 'log_book_id': log_rec.id, 'bol_order_data_queue_line_id':
                        queue_line.id, 'order_ref': bol_order_id}
                    logs.append([0, 0, vals])
                    _logger.info(message)
                log_lines = log_lines + logs
        log_rec.write({'log_lines': log_lines})
        order_queue_data = [item for item in order_queue_data if item not in order_data_temp]
        queue_line.write({'bol_order_data': json.dumps(order_queue_data) if order_queue_data else ''})
        return True

    def get_single_order_response(self, instance, bol_order_id):
        """
        This method is used to get single order response
        :param instance: Bol Instance
        :param bol_order_id: Order ID
        :return: Order Response
        @author : Ekta Bhut
        """
        response_obj, order_response = BolAPI.get('single_order', instance.bol_auth_token,
                                                  bol_order_id)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, order_response = BolAPI.get('single_order', instance.bol_auth_token,
                                                      bol_order_id)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, order_response = BolAPI.get('single_order', instance.bol_auth_token,
                                                      bol_order_id)
        if response_obj.status_code == 404:
            _logger.info("ORDER %s NOT FOUND SO SKIP IT" % bol_order_id)
            return {}
        return order_response

    def create_bol_order_ept(self, instance, queue_line, fulfillment_by, order_data, log_rec):
        """
        This method is used to Create Bol open order
        :param instance: Bol Instance
        :param fulfillment_by: FBB or FBR
        :param order_data: Order response
        :return:
        @author : Ekta Bhut
        """
        log_lines = []
        res_partner_obj = self.env['res.partner']
        partner_resposne = order_data.get('billingDetails') and order_data.get('billingDetails').get(
                'email') or order_data.get('shipmentDetails') and order_data.get('shipmentDetails').get(
                'email')
        partner = res_partner_obj.search_partner_by_email(partner_resposne)
        partner_invoice_response = order_data.get('billingDetails') or order_data.get('shipmentDetails')
        partner_invoice_id = self.search_or_create_bol_partner_ept(partner_invoice_response, partner, 'invoice')
        partner_shipping_id = self.search_or_create_bol_partner_ept(order_data.get(
                'shipmentDetails'), partner or partner_invoice_id or False, 'delivery')
        vals = self.prepare_vals_for_bol_order(instance, order_data, partner or partner_invoice_id,
                                               partner_invoice_id, partner_shipping_id,
                                               fulfillment_by)
        order = self.create(vals)
        logs, skip_order = self.create_bol_order_line(instance, queue_line, fulfillment_by, order,
                                                      order_data.get(
                                                              'orderItems'), log_rec)
        if logs:
            log_lines = log_lines + logs
        if skip_order:
            order.unlink()
            return False, log_lines
        return order, log_lines

    # Following methods are there for process bol shipped orders
    def process_bol_shipped_order_queue_line(self, instance, queue_line, fulfillment_by, log_rec):
        """
        This method is used to Process bol open order queue line.
        :param instance: Bol Instance
        :param fulfillment_by: FBB or FBR
        :param queue_line: Queue line
        :param log_rec: Common log book record
        :return:
        """
        log_lines = []
        count = 0
        shipped_queue_data = json.loads(queue_line.bol_shipped_data)
        order_data_temp = []
        for shipped_order_data in shipped_queue_data:
            count += 1
            if count == 10:
                count = 0
                self._cr.commit()
            bol_order_id = shipped_order_data.get('order').get('orderId')
            _logger.info(bol_order_id)
            date_order = shipped_order_data.get('order').get('orderPlacedDateTime')
            shipment_id = str(shipped_order_data.get('shipmentId'))
            date_order = parser.parse(date_order).astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
            order_date = datetime.strptime(date_order, '%Y-%m-%d %H:%M:%S')
            if instance.bol_import_order_after_date > order_date:
                continue
            is_order_exist = self.search_bol_order_exist_or_not(instance, bol_order_id,
                                                                fulfillment_by)
            if is_order_exist:
                order_data_temp.append(shipped_order_data)
                continue
            else:
                logs = []
                order_response = self.get_single_order_shipment_response(instance, shipment_id)
                if order_response:
                    order, logs = self.create_bol_shipped_order_ept(instance, queue_line, fulfillment_by,
                                                                    order_response, log_rec)
                    if order:
                        order.auto_workflow_process_id.shipped_order_workflow_ept(order)
                        order_data_temp.append(shipped_order_data)
                else:
                    message = "Order can not be found with open order API %s" % bol_order_id
                    vals = {'message': message, 'log_book_id': log_rec.id, 'bol_shipped_order_queue_line_id':
                        queue_line.id, 'order_ref': bol_order_id}
                    logs.append([0, 0, vals])
                    _logger.info(message)
                log_lines = log_lines + logs
        order_queue_data = [item for item in shipped_queue_data if item not in order_data_temp]
        queue_line.write({'bol_shipped_data': json.dumps(order_queue_data) if order_queue_data else ''})
        return True

    def get_single_order_shipment_response(self, instance, shipment_id):
        """
        This method is used to get single shipment response.
        :param instance: Bol Instance
        :param shipment_id: Shipment ID
        :return:
        @author : Ekta Bhut
        """
        response_obj, shipment_response = BolAPI.get('single_shipment_list', instance.bol_auth_token, shipment_id)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, shipment_response = BolAPI.get('single_shipment_list', instance.bol_auth_token,
                                                         shipment_id)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, shipment_response = BolAPI.get('single_shipment_list', instance.bol_auth_token,
                                                         shipment_id)
        if response_obj.status_code == 404:
            _logger.info("Shipment %s NOT FOUND SO SKIP IT" % shipment_id)
            return {}
        return shipment_response

    def search_bol_order_exist_or_not(self, instance, bol_order_id, fulfillment_by):
        """
        This method is used to search bol order exist or not
        :param instance: Bol Instance
        :param bol_order_id: Bol Order ID
        :param fulfillment_by: FBB or FBR
        :return: True or False
        @author : Ekta Bhut
        """
        bol_order = self.search([('bol_instance_id', '=', instance.id),
                                 ('bol_fulfillment_by', '=', fulfillment_by),
                                 ('bol_order_id', '=', bol_order_id)])
        return True if bol_order else False

    def create_bol_shipped_order_ept(self, instance, queue_line, fulfillment_by, shipped_order_data, log_rec):
        """
        This method is used to create bol shipped orders
        :param log_rec: Log book record
        :param shipped_order_data: Order data
        :param instance: Bol Instance
        :param fulfillment_by: FBB or FBR
        :return: Order , loglines
        @author : Ekta Bhut
        """
        log_lines = []
        res_partner_obj = self.env['res.partner']
        bol_order_id = shipped_order_data.get('order') and shipped_order_data.get('order').get('orderId')
        partner_resposne = shipped_order_data.get('billingDetails') and shipped_order_data.get('billingDetails').get(
                'email') or shipped_order_data.get('shipmentDetails') and shipped_order_data.get('shipmentDetails').get(
                'email')
        if not shipped_order_data.get('billingDetails') and not shipped_order_data.get('shipmentDetails'):
            message = "Billing and shipping information not found in Order %s" % bol_order_id
            vals = {'message': message, 'log_book_id': log_rec.id, 'bol_shipped_order_queue_line_id':
                queue_line.id, 'order_ref': bol_order_id}
            log_lines.append([0, 0, vals])
            return False, log_lines
        partner = res_partner_obj.search_partner_by_email(partner_resposne)
        partner_invoice_response = shipped_order_data.get('billingDetails') or shipped_order_data.get('shipmentDetails')
        partner_invoice_id = self.search_or_create_bol_partner_ept(partner_invoice_response, partner, 'invoice')
        partner_shipping_id = self.search_or_create_bol_partner_ept(shipped_order_data.get(
                'shipmentDetails'), partner or partner_invoice_id or False, 'delivery')
        vals = self.prepare_vals_for_bol_order(instance, shipped_order_data.get('order'),
                                               partner or partner_invoice_id,
                                               partner_invoice_id, partner_shipping_id,
                                               fulfillment_by)
        order = self.create(vals)
        logs, skip_order = self.with_context(shipped_order=True).create_bol_order_line(instance, queue_line,
                                                                                       fulfillment_by,
                                                                                       order,
                                                                                       shipped_order_data.get(
                                                                                               'shipmentItems'),
                                                                                       log_rec)
        _logger.info("FBB order is importing {0}".format(shipped_order_data.get('order').get('orderId')))
        if logs:
            log_lines = log_lines + logs
        if skip_order:
            order.unlink()
            return False, log_lines
        return order, log_lines

    def import_bol_order_by_id(self, instance, order_id, log_rec):
        """
        This method is used to import order by IDs
        :param instance: Bol Instance
        :param order_id: Order ID
        :param log_rec: Log book record
        :return:
        """
        order_response = self.get_single_order_response(instance, order_id)
        log_lines = []
        if order_response:
            bol_order_id = order_id
            date_order = order_response.get('orderPlacedDateTime')
            date_order = parser.parse(date_order).astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
            order_date = datetime.strptime(date_order, '%Y-%m-%d %H:%M:%S')
            fulfillment_by = order_response.get('orderItems')[0].get('fulfilment').get('method')
            if instance.bol_import_order_after_date > order_date:
                message = "Order %s is not imported because it is created before %s, Creation time: %s" % (
                    bol_order_id, instance.bol_import_order_after_date, order_date)
                vals = {'message': message, 'log_book_id': log_rec.id, 'order_ref': bol_order_id}
                log_lines.append([0, 0, vals])
                _logger.info(message)
                return log_lines
            is_order_exist = self.search_bol_order_exist_or_not(instance, bol_order_id,
                                                                fulfillment_by)
            if is_order_exist:
                return log_lines
            else:
                order_response = self.get_single_order_response(instance, bol_order_id)
                if order_response:
                    order, logs = self.create_bol_order_ept(instance, False, fulfillment_by,
                                                            order_response, log_rec)
                    if order:
                        order.process_orders_and_invoices_ept()
                else:
                    message = "Order can not be found with open order API %s" % bol_order_id
                    vals = {'message': message, 'log_book_id': log_rec.id, 'order_ref': bol_order_id}
                    log_lines.append([0, 0, vals])
                    _logger.info(message)
        return log_lines

    # Following methods are used in both process
    def search_or_create_bol_partner_ept(self, partner_dict, parent_id, address_type):
        """
        This method is used to create or search shipping or invoice partner
        :param parent_id: customer parent id
        :param partner_dict: partner response
        :param address_type: shipping,invoice,customer
        :return:
        """
        res_partner_obj = self.env['res.partner']
        partner_vals = {}
        if partner_dict.get('firstName', ''):
            name = "{0} {1}".format(partner_dict.get('firstName', ''), partner_dict.get('surname', ''))
        else:
            name = partner_dict.get('email')
        partner_vals.update({'name': name,
                             'street': "{0}{1} {2}".format(partner_dict.get('houseNumber', ''),
                                                           partner_dict.get(
                                                               'houseNumberExtension', ''),
                                                           partner_dict.get('streetName', '')),
                             'street2': partner_dict.get('extraAddressInformation', False),
                             'vat': partner_dict.get('vatNumber', ''),
                             'city': partner_dict.get('city'),
                             'email': partner_dict.get('email'),
                             'zip': partner_dict.get('zipCode'),
                             'phone': partner_dict.get('deliveryPhoneNumber', ''),
                             'customer_rank': 1})
        if not partner_vals.get('name', ''):
            partner_vals.update({'name': partner_vals.get('email')})
        country_id = partner_dict.get('countryCode') and res_partner_obj.get_country(
            partner_dict.get('countryCode')) or False
        partner_vals.update({'country_id': country_id.id})
        address_key_list = ["name", "street", "street2", "city", "zip", "phone", "country_id"]
        # search partner based on email.
        # partner = res_partner_obj.search_partner_by_email(partner_vals.get('email'))
        extra_domain = [('type', '=', address_type)]
        if parent_id:
            extra_domain.append(('parent_id', '=', parent_id.id))
        # if partner:
        partner = res_partner_obj._find_partner_ept(partner_vals, address_key_list, extra_domain)
        if not partner:
            partner = res_partner_obj._find_partner_ept(partner_vals, address_key_list, [])
        if not partner:
            partner_vals.update({'type': address_type, 'is_company': False, 'is_bol_customer': True})
            partner = res_partner_obj.create(partner_vals)
        return partner

    def get_bol_order_name(self, instance, fulfillment_by, bol_order_id):
        """
        Get Bol Order name
        :param instance: Bol Instance
        :param fulfillment_by: FBR & FBB
        :param bol_order_id: Bol Order ID
        :return: Name
        @author : Ekta Bhut
        """
        name = str(bol_order_id)
        prefix = instance.fbb_bol_order_prefix if fulfillment_by == 'FBB' else instance.fbr_bol_order_prefix
        if prefix:
            name = prefix + name
        return name

    def prepare_vals_for_bol_order(self, instance, order_data, partner_id, partner_invoice_id,
                                   partner_shipping_id,
                                   fulfillment_by):
        """
        Prepare Order vals for Bol.com
        :param instance: Bol Instance
        :param order_data: Order response
        :param partner_id: Partner
        :param partner_invoice_id: Invoice Partner
        :param partner_shipping_id: Shipping partner
        :param fulfillment_by: FBB or FBR
        :return: order vals
        @author : Ekta Bhut
        """
        vals = {}
        date_order = order_data.get('orderPlacedDateTime')
        date_order = parser.parse(date_order).astimezone(utc).strftime('%Y-%m-%d %H:%M:%S')
        # name = self.get_bol_order_name(instance, fulfillment_by, order_data.get('orderId'))
        workflow_id = instance.fbb_auto_workflow_id if fulfillment_by == 'FBB' else instance.fbr_auto_workflow_id
        vals.update({'patner_id': partner_id.id,
                     # 'name': name,
                     'partner_invoice_id': partner_invoice_id.id,
                     'partner_shipping_id': partner_shipping_id.id,
                     'bol_order_id': order_data.get('orderId'),
                     'bol_instance_id': instance.id,
                     'bol_fulfillment_by': fulfillment_by,
                     'client_order_ref': order_data.get('orderId'),
                     "company_id": instance.company_id.id if instance.company_id else False,
                     "warehouse_id": instance.bol_fbb_warehouse_id.id if fulfillment_by == 'FBB' else
                     instance.bol_fbr_warehouse_id.id,
                     "pricelist_id": instance.bol_pricelist_id.id,
                     "state": "draft",
                     "team_id": instance.bol_team_id.id,
                     "date_order": date_order,
                     "picking_policy": workflow_id.picking_policy
                     })
        ordervals = self.create_sales_order_vals_ept(vals)
        ordervals.update({'partner_id': partner_id.id,
                          'partner_invoice_id': partner_invoice_id.id,
                          'partner_shipping_id': partner_shipping_id.id,
                          'bol_instance_id': instance.id,
                          'bol_fulfillment_by': fulfillment_by,
                          'auto_workflow_process_id': workflow_id.id,
                          'bol_order_id': order_data.get('orderId'),
                          'payment_term_id': instance.bol_payment_term_id.id,
                          'picking_policy': workflow_id.picking_policy})
        # 'name': name

        if (not instance.is_default_sequence_fbb_sales_order) if fulfillment_by == 'FBB' else (
                not instance.is_default_sequence_fbr_sales_order):
            name = self.get_bol_order_name(instance, fulfillment_by, order_data.get('orderId'))
            ordervals.update({'name': name})

        return ordervals

    def create_bol_order_line(self, instance, queue_line, fulfillment_by, order, order_line_data, log_rec):
        """
        Create Bol order line
        :param instance: Bol Instance
        :param fulfillment_by: FBB or FBR
        :param order: Order
        :param order_line_data: Order line response
        :return:
        @author : Ekta Bhut
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        context = dict(self._context)
        bol_offer_obj = self.env['bol.offer.ept']
        sale_order_line_obj = self.env['sale.order.line']
        log_lines = []
        bol_order_id = order.bol_order_id
        skip_order = False
        for order_line in order_line_data:
            offer_data = order_line.get('offer', {})
            bol_offer_id = offer_data.get('offerId')
            bol_sku = offer_data.get('reference')
            ean = order_line.get('product').get('ean')
            name = order_line.get('product').get('title')
            order_item_id = order_line.get('orderItemId')
            bol_product = bol_offer_obj.search_bol_product(bol_offer_id, bol_sku, ean,
                                                           instance, fulfillment_by)
            if not bol_product and instance.bol_auto_create_product:
                bol_product = bol_offer_obj.sync_product(instance, log_rec, bol_offer_id,
                                                         update_price=True,
                                                         auto_create_product=True)

            if not bol_product:
                message = "Odoo product is not found with SKU {0} or EAN number {1}".format(
                        bol_sku, ean)
                vals = {'message': message, 'log_book_id': log_rec.id, 'order_ref': bol_order_id}
                if context.get('shipped_order'):
                    vals.update({'bol_shipped_order_queue_line_id': queue_line.id})
                else:
                    vals.update({'bol_order_data_queue_line_id': queue_line.id})
                log_lines.append([0, 0, vals])
                skip_order = True
                continue
            if not skip_order:
                product = bol_product.odoo_product_id
                uom_id = product and product.uom_id and product.uom_id.id or False
                line_vals = {
                    'product_id': product and product.ids[0] or False,
                    'order_id': order.id,
                    'company_id': order.company_id.id,
                    'product_uom': uom_id,
                    'name': name,
                    'price_unit': float(order_line.get('unitPrice')),
                    'order_qty': float(order_line.get('quantity')),
                    'bol_order_item_id': order_item_id
                }
                order_line_vals = sale_order_line_obj.create_sale_order_line_ept(line_vals)
                order_line_vals.update({'bol_order_item_id': order_item_id})
                order_line = sale_order_line_obj.create(order_line_vals)
        return log_lines, skip_order

    def _prepare_invoice(self):
        """
        This method used set a Bol instance in customer invoice.
        @param : self
        @return: inv_val
        @author: Ekta Bhut
        """
        inv_val = super(SaleOrder, self)._prepare_invoice()
        if self.bol_instance_id:
            inv_val.update({'bol_instance_id': self.bol_instance_id.id,
                            'bol_fulfillment_by': self.bol_fulfillment_by})
        return inv_val

    def update_order_status_in_bol(self, instance):
        """
        This method is used to update bol order status
        :param instance: Bol Instance
        :return:
        @author : Ekta Bhut
        """
        picking_ids = self.search_picking_for_update_order_status(instance)
        count = 0
        for picking in picking_ids:
            count += 1
            if count == 10:
                count = 0
                self._cr.commit()
            picking_vals = {}
            order = picking.sale_id
            _logger.info("Order status is going to update {0}".format(order.name))
            if not picking.carrier_tracking_ref:
                _logger.info("Tracking reference is not found for Order {0} , SO SKIP IT".format(order.name))
                continue
            update_vals = self.prepare_update_order_status_data_for_bol(picking)
            response, status_code = self.update_order_status_via_bol_api(instance, update_vals)
            if status_code == 400:
                _logger.info("Some issue in the Updated data {0}".format(update_vals))
                continue
            if status_code == 202:
                picking_vals.update({'process_status': response.get('status'),
                                     'updated_in_bol': True})
                _logger.info("Order status is updated {0}".format(order.name))
            shipment_response = picking.get_single_shipment_order_response(instance, order.bol_order_id)
            if shipment_response:
                shipment_response = shipment_response.get('shipments') and shipment_response.get('shipments')[0] or {}
                shipment_response and picking_vals.update({'bol_shipment_id': shipment_response.get('shipmentId', ''),
                                                           'bol_trasport_id': shipment_response.get('transport')
                                                                              and shipment_response.get(
                                                                   'transport').get('transportId', '')})
            picking.write(picking_vals)

    def search_picking_for_update_order_status(self, instance):
        """
        Search Delivery order for Update order status
        :param instance: Bol Instance
        :return: Picking_ids
        @author : Ekta Bhut
        """
        location_obj = self.env["stock.location"]
        stock_picking_obj = self.env["stock.picking"]
        customer_locations = location_obj.search([("usage", "=", "customer")])
        picking_ids = stock_picking_obj.search([("bol_instance_id", "=", instance.id),
                                                ("updated_in_bol", "=", False),
                                                ("state", "=", "done"),
                                                ("location_dest_id", "in", customer_locations.ids),
                                                ('canceled_in_bol', '=', False),
                                                ('bol_fulfillment_by', '=', 'FBR')],
                                               order="date")
        return picking_ids

    def prepare_update_order_status_data_for_bol(self, picking):
        """
        Prepare data for Update order status
        :param picking: Delivery Order
        :return:
        @author : Ekta Bhut
        """
        update_data = {}
        order_line_items = []
        bol_order_item_ids = set(picking.move_lines.mapped('sale_line_id').mapped('bol_order_item_id'))
        for line in list(bol_order_item_ids):
            order_line_items.append({'orderItemId': line})
        bol_carrier_code = picking.carrier_id and picking.carrier_id.bol_delivery_carrier_code_id and \
                           picking.carrier_id.bol_delivery_carrier_code_id.code or ''
        transport_dict = {'transporterCode': bol_carrier_code,
                          'trackAndTrace': picking.carrier_tracking_ref}
        update_data.update({'orderItems': order_line_items,
                            'transport': transport_dict})
        return update_data

    def update_order_status_via_bol_api(self, instance, vals):
        response_obj, shipment_response = BolAPI.put('update_order_status', instance.bol_auth_token, '', vals)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, shipment_response = BolAPI.put('update_order_status', instance.bol_auth_token, '', vals)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, shipment_response = BolAPI.put('update_order_status', instance.bol_auth_token, '', vals)
        if response_obj.status_code == 400:
            _logger.info("Some issue in the requested data")
            return {}, response_obj.status_code
        return shipment_response, response_obj.status_code

    @api.model
    def auto_update_fbr_order_status(self, ctx={}):
        """
        This method is called from Scheduler
        :param ctx: Argument
        :return:
        @author : Ekta Bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = ctx.get('bol_instance_id')
        if instance_id:
            instance = bol_instance_obj.browse(instance_id)
            self.update_order_status_in_bol(instance)
