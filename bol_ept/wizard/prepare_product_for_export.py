# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.

import base64
import logging

from csv import DictWriter
from datetime import datetime
from io import StringIO

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger("Bol Export Product")


class PrepareProductForExport(models.TransientModel):
    """
    Model for exporting Odoo Products into CSV file for mapping with Bol Offers.
    @author: Maulik Barad on Date 11-Apr-2020.
    """
    _name = "bol.prepare.product.for.export.ept"
    _description = "Bol Prepare Product For Export"

    offer_fulfilled_by = fields.Selection([("fbr", "FBR"), ("fbb", "FBB")])
    csv_file = fields.Binary()
    file_name = fields.Char(help="Name of CSV file.")

    def prepare_product_for_export(self):
        """
        This method is used to export products in CSV file as per selection.
        It will export product data in CSV file, if user want to do some changes and want to map the Bol Offers with
        proper Odoo Products.
        @author: Maulik Barad on Date 26-Feb-2021.
        """
        _logger.info("Starting product exporting via CSV file...")

        active_template_ids = self._context.get("active_ids", [])
        products = self.env["product.product"].browse(active_template_ids)
        products = products.filtered(lambda template: template.type == "product")
        if not products:
            raise UserError(_("It seems like selected products are not Storable products."))

        return self.export_offers_csv_file(products)

    def export_offers_csv_file(self, products):
        """
        This method is used for export the odoo products in csv file.
        :param self: It contain the current class Instance
        :param product_templates: Records of odoo template.
        @author:
        """
        buffer = StringIO()
        field_names = ["product_name", "product_default_code", "bol_reference_code", "fulfillment_by", "PRODUCT_ID"]

        csv_writer = DictWriter(buffer, field_names, delimiter=",")
        csv_writer.writer.writerow(field_names)

        rows = []
        for product in products.filtered(lambda variant: variant.default_code):
            row = self.prepare_bol_offer_data_for_csv(product)
            rows.append(row)

        if not rows:
            raise UserError(_("No data found to be exported.\n\nPossible Reasons:\n   - SKU(s) are not set properly."))
        csv_writer.writerows(rows)
        buffer.seek(0)
        file_data = buffer.read().encode()
        self.write({
            "csv_file": base64.encodebytes(file_data),
            "file_name": "Bol_export_product"
        })

        return {
            "type": "ir.actions.act_url",
            "url": "web/content/?model=bol.prepare.product.for.export.ept&id=%s&field=csv_file&download=true&"
                   "filename=%s.csv" % (self.id, self.file_name + str(datetime.now().strftime("%d/%m/%Y:%H:%M:%S"))),
            "target": self
        }

    def prepare_bol_offer_data_for_csv(self, product):
        """ This method is used to prepare a row data of csv file.
            @param : self
            @return: row
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 26 October 2020.
            Task_id: 167537 - Code refactoring
        """
        row = {
            "product_name": product.name,
            "product_default_code": product.default_code,
            "bol_reference_code": product.default_code,
            "fulfillment_by": self.offer_fulfilled_by,
            "PRODUCT_ID": product.id,
        }
        return row
