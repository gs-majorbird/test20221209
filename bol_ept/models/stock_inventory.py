# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import logging
import time

from odoo import models, fields

from ..bol_api.bol_api import BolAPI

_logger = logging.getLogger(__name__)

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    bol_instance_id = fields.Many2one('bol.instance.ept', "Instance")

    def import_fbb_stock_ept(self, instance):
        """ This method is used to import stock from the FBB.
            : param instance: Record of instance.
            @author: Ekta bhut
        """
        bol_instance_obj = self.env['bol.instance.ept']
        ir_model_obj = self.env['ir.model']
        model_id = ir_model_obj.search([('model', '=', 'stock.inventory')])
        list_of_inventory = []
        log_lines = []
        offers, log_lines = self.get_inventory_from_fbb(instance, model_id, log_lines)
        if isinstance(offers, bool) and log_lines:
            self.bol_create_job_log_book('import', instance, model_id, log_lines)
            return True
        fbb_inventory, unsaleable_inventory, log_lines = self.prepare_data_for_inventory_adjustment(offers, instance,
                                                                                                    model_id, log_lines)
        if log_lines:
            self.bol_create_job_log_book('import', instance, model_id, log_lines)
        if fbb_inventory:
            list_of_inventory.append(fbb_inventory.id)
        if unsaleable_inventory:
            list_of_inventory.append(unsaleable_inventory.id)
        return list_of_inventory

    def get_inventory_from_fbb(self, instance, model_id, log_lines):
        """
        This method is used to request for the inventory import from FBB.
        :param instance: Bol Instance
        :param model_id: Model Id
        :param log_lines: Log lines
        :return:
        @author: Ekta bhut
        """
        common_log_line = self.env['common.log.lines.ept']
        offers = []
        page = 0
        try:
            while True:
                page = page + 1
                page_number = "page=%s" % page
                response_obj, response = BolAPI.get('inventory', instance.bol_auth_token, page_number)
                if response_obj.status_code in [400, 401]:
                    instance.get_bol_token()
                    response_obj, response = BolAPI.get('inventory', instance.bol_auth_token, page_number)
                if not response:
                    break
                _logger.info(page)
                if response.get('inventory'):
                    offers = offers + response.get('inventory')
                else:
                    break
        except Exception as error:
            log_line = common_log_line.bol_create_order_log_line(error, model_id.id, False, False)
            log_lines.append(log_line.id)
            return False, log_lines

        return offers, log_lines

    def prepare_data_for_inventory_adjustment(self, offers, instance, model_id, log_lines):
        """
        This method is used to prepare data(which receive from bol.com) for the inventory adjustment.
        :param offers: Bol offers
        :param instance: Instance
        :param model_id: Model ID
        :param log_lines: Log lines
        :return:
        @author : Ekta Bhut
        """
        common_log_line = self.env['common.log.lines.ept']
        bol_product_obj = self.env['bol.offer.ept']
        saleable_product_inventory = []
        unsaleable_product_inventory = []
        location_id = instance.bol_fbb_warehouse_id.lot_stock_id
        unsaleable_location_id = instance.bol_fbb_warehouse_id.bol_unsaleable_location_id
        fbb_inventory = False
        fbb_unsaleable_inventory = False
        for offer in offers:
            ean = offer.get('ean')
            stock = offer.get('regularStock', 0)
            unsaleable_stock = offer.get('gradedStock', 0)
            bol_product = bol_product_obj.search(
                    [('fulfillment_by', '=', 'FBB'), ('bol_instance_id', '=', instance.id), ('ean_product', '=', ean)],
                    limit=1)
            if not bol_product:
                message = "Product with EAN %s is not found in Odoo" % (ean),
                log_line = common_log_line.bol_create_order_log_line(message, model_id.id, False, False)
                log_lines.append(log_line.id)
                continue
            if stock > 0:
                saleable_product_inventory.append({
                    'product_id': bol_product.odoo_product_id,
                    'product_qty': stock,
                    'location_id': location_id.id
                })
            if unsaleable_stock > 0:
                unsaleable_product_inventory.append({
                    'product_id': bol_product.odoo_product_id,
                    'product_qty': unsaleable_stock,
                    'location_id': location_id.id
                })
        if saleable_product_inventory:
            fbb_inventory = saleable_product_inventory and self.env['stock.inventory'].create_stock_inventory_ept(
                    products=saleable_product_inventory, location_id=location_id,
                    auto_validate=instance.auto_validate_inventory)
            inventory_name = "Saleable Instance : %s %s" % (instance.name, time.strftime("%Y-%m-%d %H:%M:%S"))
            fbb_inventory.write({'bol_instance_id': instance.id, 'name': inventory_name})
        if unsaleable_product_inventory:
            fbb_unsaleable_inventory = unsaleable_product_inventory and self.env[
                'stock.inventory'].create_stock_inventory_ept(
                    products=unsaleable_product_inventory, location_id=unsaleable_location_id,
                    auto_validate=instance.auto_validate_inventory)
            unsaleable_inventory_name = "Unsaleable Inventory : %s %s" % (
            instance.name, time.strftime("%Y-%m-%d %H:%M:%S"))
            fbb_unsaleable_inventory.write({'bol_instance_id': instance.id, 'name': unsaleable_inventory_name})

        return fbb_inventory, fbb_unsaleable_inventory, log_lines

    def bol_create_job_log_book(self, operation_type, instance, model_id, log_lines):
        """
         This method is used to create a log book record.
        :param operation_type:
        :param instance:
        :param model_id:
        :param log_lines:
        :return:
        @author : Ekta Bhut
        """
        log_book_obj = self.env['common.log.book.ept']
        log_book_id = log_book_obj.create({
            'active': True,
            'type': operation_type,
            'bol_instance_id': instance.id if instance else False,
            'model_id': model_id.id if model_id else False,
            'res_id': self.id,
            'module': 'bol_ept',
            'log_lines': [(6, 0, log_lines)]
        })
        return log_book_id
