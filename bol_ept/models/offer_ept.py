# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time
from datetime import datetime, timedelta

from odoo import models, fields, api, _

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class BolOfferEpt(models.Model):
    _name = "bol.offer.ept"
    _description = "Bol Offer"

    name = fields.Char()
    odoo_product_id = fields.Many2one("product.product", ondelete="cascade",
                                      help="ERP Product Reference", string="Odoo Product")
    bol_bsku = fields.Char('Bol SKU')
    ean_product = fields.Char('Bol EAN number')
    bol_instance_id = fields.Many2one("bol.instance.ept", string="Instance")
    bol_offer_id = fields.Char("Bol Offer ID", help="Id of the Offer in Bol.")
    fix_stock_type = fields.Selection([('fix', 'Fix'), ('percentage', 'Percentage')],)
    fix_stock_value = fields.Float()
    fulfillment_by = fields.Selection([('FBR', 'Fulfilled by the Retailer'),
                                       ('FBB', 'Fulfilment by Bol.com')],)
    is_publish = fields.Boolean("Is Published?")
    product_description = fields.Text(string="Description")
    reference_code = fields.Char()
    exported_in_bol = fields.Boolean('Exported in Bol?')
    active = fields.Boolean(default=True)

    def sync_product(self, instance_id, log_rec, product_offerid='', update_price=False,
                     auto_create_product=False):
        """
        This method used to sync product from bol.com
        :param instance_id: Bol Instance
        :param log_rec: Common log book record
        :param product_offerid: Offer ID
        :param update_price: Boolean, should update product price or not.
        :param auto_create_product: Boolean, Auto create odoo product or not
        :return: Bol Offer
        @author : Ekta Bhut
        """
        if not instance_id:
            raise Warning(_("Instance not Available, Can't Process ahead."))
        product_obj = self.env['product.product']
        transaction_log_obj = self.env['common.log.lines.ept']
        bol_offer_obj = self.env['bol.offer.ept']
        bol_products = self.get_product_details(instance_id, product_offerid, log_rec)
        if not bol_products:
            return True
        default_code = bol_products.get('reference_code', '')
        ean = bol_products.get('ean_product', '')
        fulfilment_by = bol_products.get('fulfillment_by', 'FBR')
        price = bol_products.get('price', '')
        price_list_id = instance_id.bol_pricelist_id
        del bol_products['price']
        bol_product = self.search_bol_product(product_offerid, default_code, ean, instance_id,
                                              fulfillment_by=fulfilment_by)
        bol_products.update({'exported_in_bol': True})
        if bol_product:
            bol_product.write(bol_products)
            if update_price:
                price_list_id.set_product_price_ept(bol_product.odoo_product_id.id, price)
        else:
            odoo_product = self.search_odoo_product(default_code, ean)
            bol_products.update({'odoo_product_id': odoo_product.id, 'exported_in_bol': True,
                                 'bol_offer_id': product_offerid, 'bol_instance_id': instance_id.id})
            if odoo_product:
                bol_offer_obj.create(bol_products)
                if update_price:
                    price_list_id.set_product_price_ept(odoo_product.id, price)
            if not odoo_product and auto_create_product:
                odoo_product = product_obj.create({'default_code': default_code,
                                                   'barcode': ean,
                                                   'name': bol_products.get('name'),
                                                   'type': 'product'})
                bol_products.update({'odoo_product_id': odoo_product.id})
                bol_product = bol_offer_obj.create(bol_products)
                if update_price:
                    price_list_id.set_product_price_ept(odoo_product.id, price)
            else:
                not_found_msg = """ Line Skipped due to product not found with internal reference
                %s || Instance %s """ % (default_code, instance_id.name)
                transaction_vals = {'default_code': default_code, 'message': not_found_msg,
                                    'log_book_id': log_rec.id}
                transaction_log_obj.create(transaction_vals)
        return bol_product

    def search_bol_product(self, product_offerid, default_code, ean, instance_id, fulfillment_by):
        """
        This method is used to search bol product
        :param product_offerid: Bol Offer ID
        :param default_code: Product default code
        :param ean: Product EAN
        :param instance_id: Bol Instance ID
        :param fulfillment_by: FBR & FBB
        :return: Bol product
        @author : Ekta Bhut
        """
        bol_product = self.with_context(active_test=True).search([('bol_offer_id', '=', product_offerid),
                                                                  ('bol_instance_id', '=', instance_id.id),
                                                                  ('fulfillment_by', '=', fulfillment_by)])
        if not bol_product:
            bol_product = self.with_context(active_test=True).search([('reference_code', '=', default_code),
                                                                      ('bol_instance_id', '=', instance_id.id),
                                                                      ('fulfillment_by', '=', fulfillment_by)])
        if not bol_product:
            bol_product = self.with_context(active_test=True).search([('ean_product', '=', ean),
                                                                      ('bol_instance_id', '=', instance_id.id),
                                                                      ('fulfillment_by', '=', fulfillment_by)])
        if not bol_product:
            return False
        if not bol_product.active:
            bol_product.write({'active': True})
        return bol_product

    def search_odoo_product(self, default_code, ean):
        """
        This method is used to search Odoo product based on Default code and EAN
        :param default_code: Default code
        :param ean: EAN number
        :return: Odoo Product
        @author : Ekta Bhut
        """
        product_obj = self.env['product.product']
        odoo_product = product_obj.search([('default_code', '=', default_code)], limit=1)
        if not odoo_product:
            odoo_product = product_obj.search([('barcode', '=', ean)], limit=1)
        return odoo_product

    def get_bol_single_offer_response(self, instance_id, offer_id, log_rec):
        """
        This method is used to get bol offer response
        :param instance_id: Bol Instance
        :param offer_id: Offer ID
        :param log_rec: Log book record
        :return: Product data
        @author : Ekta Bhut
        """
        product_data = {}
        transaction_log_obj = self.env['common.log.lines.ept']
        try:
            response_obj, product_data = BolAPI.get('offer', instance_id.bol_auth_token, offer_id)
            if response_obj.status_code in [401, 404]:
                instance_id.get_bol_token()
                response_obj, product_data = BolAPI.get('offer', instance_id.bol_auth_token,
                                                        offer_id)
        except Exception as e:
            transaction_vals = {'message': e,
                                'log_book_id': log_rec.id}
            transaction_log_obj.create(transaction_vals)
            return False, product_data
        return response_obj, product_data

    def get_product_details(self, instance_id, offer_id, log_rec):
        """
        This method is used to prepare data for product
        :param instance_id: Bol instance
        :param offer_id: Offer ID
        :param log_rec: Log book record
        :return: Product dats
        @author : Ekta Bhut
        """
        transaction_log_obj = self.env['common.log.lines.ept']
        response_obj, product_data = self.get_bol_single_offer_response(instance_id, offer_id,
                                                                        log_rec)
        if not product_data and response_obj.status_code not in [202, 200]:
            transaction_vals = {'message': "Product sync operation stop because data not found "
                                           "with this Offer Id:-%s || Instance:-%s" % (
                                               offer_id, instance_id.name),
                                'log_book_id': log_rec.id}
            transaction_log_obj.create(transaction_vals)
            return {}
        price = 0.0
        for price_dict in product_data.get('pricing').get('bundlePrices'):
            if price_dict.get('quantity') == 1:
                price = price_dict.get('unitPrice')
        product = {
            'bol_offer_id': product_data.get('offerId'),
            'name': product_data.get("store") and product_data.get("store").get("productTitle") or "",
            'ean_product': product_data.get('ean', ''), 'price': price,
            # 'condition':product_data.get('condition', {}).get('name', ''),
            'is_publish': product_data.get('onHoldByRetailer'),
            'reference_code': product_data.get("reference", ''),
            'exported_in_bol': True,
            'fulfillment_by': product_data.get("fulfilment") and product_data.get("fulfilment").get("method") or ""
        }
        return product

    def create_sync_active_products(self, instance_id, update_price_in_pricelist,
                                    auto_create_product):
        """
        Process will create record of Active Product List of selected bol instance
        @:param - instance_id - selected instance from wizard
        @:param - update_price_in_pricelist - Boolean for create pricelist or not
        @:param - auto_create_product - Boolean for create product or not
        @author: Ekta Bhut
        """
        bol_product_sync_obj = self.env['bol.product.sync.ept']
        vals = {'bol_instance_id': instance_id.id,
                'update_price_in_pricelist': update_price_in_pricelist or False,
                'auto_create_product': auto_create_product or False}

        sync_product_id = bol_product_sync_obj.create(vals)
        action = self.env.ref('bol_ept.action_bol_product_sync_ept', False)
        result = action and action.sudo().read()[0] or {}
        res = self.env.ref('bol_ept.bol_product_sync_form_view_ept', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = sync_product_id and sync_product_id.id or False
        return result

    def export_product_stock_to_bol(self, instance, offer_ids):
        """
        This method is used to export product stock
        :param instance: Bol Instance
        :param offer_ids: Offer IDs
        :return: True
        @author : Ekta Bhut
        """
        context = dict(self._context)
        product_obj = self.env['product.product']
        export_stock_from_date = instance.inventory_last_sync_on
        if not export_stock_from_date:
            export_stock_from_date = datetime.now() - timedelta(30)
        if context.get('call_from_bol_cron'):
            instance.write({'inventory_last_sync_on': datetime.now()})
        odoo_products_ids = product_obj.get_products_based_on_movement_date_ept(export_stock_from_date,
                                                                                instance.company_id)
        if not offer_ids:
            offer_ids = self.search([('bol_instance_id', '=', instance.id), ('exported_in_bol', '=', True),
                                     ('fulfillment_by', '=', 'FBR')])
        offer_ids = offer_ids.filtered(lambda l: l.odoo_product_id.id in odoo_products_ids)
        odoo_products_ids = offer_ids.mapped('odoo_product_id').ids
        product_stock_data = self.check_stock_type_and_get_product_stock(instance, odoo_products_ids)
        for offer in offer_ids:
            stock = self.get_product_stock(offer, product_stock_data)
            response = self.export_stock_to_bol_via_api(instance, offer, stock)
        return True

    def get_product_stock(self, offer, product_stock_data):
        """
        This method is used to get product stock based on configuration
        :param offer: Bol Offer
        :param product_stock_data: Product stock data
        :return: Product stock
        @author : Ekta Bhut
        """
        product_stock = product_stock_data.get(offer.odoo_product_id.id)
        if offer.fix_stock_type == 'fix' and offer.fix_stock_value < product_stock:
            product_stock = offer.fix_stock_value
        if offer.fix_stock_type == 'percentage':
            percentage_stock = int((product_stock * offer.fix_stock_value) / 100.0)
            if percentage_stock < product_stock:
                product_stock = percentage_stock
        return product_stock

    def export_stock_to_bol_via_api(self, instance, offer, quantity):
        """
        This method is used to export stock with API
        :param offer: Bol Offer
        :param quantity: Quantity
        :return: Response
        """
        bol_offer_id = '{0}/stock'.format(offer.bol_offer_id)
        payload = {
            "amount": int(quantity),
            "managedByRetailer": True
        }
        response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code == 404:
            _logger.info("STOCK IS NOT EXPORTED FOR OFFER ID -- {0}".format(offer.bol_offer_id))
            return {}
        if response_obj.status_code == 202:
            _logger.info("Stock is successfully exported for offer ID {0} & quantity {1}".format(offer.bol_offer_id,
                                                                                                 int(quantity)))
        return product_response

    def check_stock_type_and_get_product_stock(self, instance, product_ids):
        """
        This method is used to get product stock data based on the Instance configuration
        :param instance:  Bol Instance
        :param product_ids:  Product IDs
        :return: Product stock data
        @author : Ekta Bhut
        """
        prod_obj = self.env['product.product']
        warehouse = instance.bol_fbr_warehouse_id
        products_stock = False
        if product_ids:
            if instance.stock_field == 'free_qty':
                products_stock = prod_obj.get_free_qty_ept(warehouse, product_ids)
            elif instance.stock_field == 'virtual_available':
                products_stock = prod_obj.get_forecasted_qty_ept(warehouse, product_ids)
        return products_stock

    def export_price_to_bol(self, instance, offer_ids):
        """
        This method is used to export price to Bol.com
        :param instance: Bol.com Instance
        :param offer_ids: Bol offer ids
        :return:
        @author : Ekta Bhut
        """
        log_book_obj = self.env['common.log.book.ept']
        common_log_line = self.env['common.log.lines.ept']
        if not offer_ids:
            offer_ids = self.search([('bol_instance_id', '=', instance.id), ('exported_in_bol', '=', True),
                                     ('fulfillment_by', '=', 'FBR')])
        message = "Perform Operation for export Product Price"
        model_id = self.env['ir.model']._get('bol.offer.ept').id
        bol_job = log_book_obj.bol_create_common_log_book('export', self.bol_instance_id, model_id,
                                                          message, self.id)
        for offer in offer_ids:
            price = offer.bol_instance_id.bol_pricelist_id.get_product_price_ept(offer.odoo_product_id)
            price = price and round(price, 2) or 0.0
            offer_id = offer.bol_offer_id
            response, status_code = self.update_product_price_to_bol_via_api(instance, offer, price)
            if status_code == 404:
                message = 'Price is not exported for the Offer {0}'.format(offer.bol_offer_id)
                log_line = common_log_line.bol_create_order_log_line(message, model_id.id, False, bol_job)
        if not bol_job.log_lines:
            bol_job.unlink()

    def update_product_price_to_bol_via_api(self, instance, offer, price):
        """
        This method use to connect with Bol.com and it will export price to bol.com
        :param instance: Bol Instance
        :param offer: Bol Offer
        :param price: Price
        :return: Response code
        @author : Ekta Bhut
        """
        bol_offer_id = '{0}/price'.format(offer.bol_offer_id)
        payload = {
            "pricing": {
                "bundlePrices": [
                    {
                        "quantity": 1,
                        "unitPrice": price
                    }
                ]
            }
        }
        response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code in [400, 401]:
            instance.get_bol_token()
            response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code == 429:
            time.sleep(5)
            response_obj, product_response = BolAPI.put('offer', instance.bol_auth_token, bol_offer_id, payload)
        if response_obj.status_code == 404:
            _logger.info("PRICE IS NOT EXPORTED FOR OFFER -- {0}".format(offer.bol_offer_id))
            return {}, response_obj.status_code
        if response_obj.status_code == 202:
            _logger.info("Price is successfully exported for Offer {0} & Price {1}".format(offer.bol_offer_id, price))
        return product_response, response_obj.status_code

    @api.model
    def auto_update_fbr_product_stock(self, ctx={}):
        """
        This method is used to Export product price, from Scheduler
        :param ctx: Argument
        :return:
        @author : Ekta Bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        instance_id = ctx.get('bol_instance_id')
        if instance_id:
            instance = bol_instance_obj.browse(instance_id)
            self.with_context({'call_from_bol_cron': True}).export_product_stock_to_bol(instance, self)
