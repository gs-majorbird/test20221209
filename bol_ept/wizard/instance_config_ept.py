# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
from ..bol_api.bol_api import BolAPI

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BolInstanceConfigEpt(models.TransientModel):
    """
    Transient Model for Creating Bol Instance.
    @author: Maulik Barad on Date 12-Feb-2021.
    """
    _name = "bol.instance.config.ept"
    _description = "Bol Instance Configuration"

    name = fields.Char()
    client_id = fields.Char("Client ID")
    secret_id = fields.Text("Secret Key")
    # account_type = fields.Selection([("sandbox", "SandBox"), ("production", "Production")])
    bol_fulfillment_by = fields.Selection([("FBR", "FBR"), ("FBB", "FBB"), ("Both", "FBR & FBB")],
                                          string="Fulfilment By", default="FBR")
    bol_country_id = fields.Many2one("res.country", string="Country")
    company_id = fields.Many2one("res.company", help="All transactions will be done based on selected company")

    def create_bol_instance(self):
        """
        This method is used to create Bol Instance.
        @author: Maulik Barad on Date 13-Feb-2021.
        """
        res_lang_obj = self.env["res.lang"]
        instance_exist = self.env["bol.instance.ept"].search([("client_id", "=", self.client_id),
                                                              ("secret_id", "=", self.secret_id)])
        if instance_exist:
            raise UserError(_("Instance already exist with given Credential."))
        try:
            result = BolAPI.get_bol_token(self.client_id, self.secret_id)
            if not result.get("access_token"):
                raise UserError(_("Given Credentials are incorrect, please provide Correct Credentials."))
            bol_auth_token = "Bearer" + " " + result.get("access_token")
        except Exception as error:
            raise UserError(_("Something went wrong.\n%s") % str(error))

        if bol_auth_token:
            bol_pricelist_id = self.get_bol_pricelist_id()
            fbr_warehouse_id = self.get_bol_fbr_warehouse()
            fbb_warehouse_id = self.get_bol_fbb_warehouse()
            team_id = self.create_bol_sales_team(self.name)
            lang_id = res_lang_obj.search([("code", "=", self._context.get("lang"))])
            if not lang_id:
                lang_id = res_lang_obj.search([("active", "=", True)], limit=1)
            vals = {
                "name": self.name,
                "client_id": self.client_id,
                "secret_id": self.secret_id,
                "bol_auth_token": bol_auth_token,
                # "account_type": self.account_type,
                "bol_country_id": self.bol_country_id.id,
                "company_id": self.company_id.id,
                "bol_fulfillment_by": self.bol_fulfillment_by,
                "bol_pricelist_id": bol_pricelist_id and bol_pricelist_id.id or False,
                "bol_fbb_warehouse_id": fbb_warehouse_id or False,
                "bol_fbr_warehouse_id": fbr_warehouse_id or False,
                "bol_lang_id": lang_id and lang_id.id or False,
                "bol_team_id": team_id and team_id.id or False,
                "state": "confirmed"
            }
            try:
                instance = self.env["bol.instance.ept"].create(vals)
                self.create_bol_fpos_ept(instance)
            except Exception as error:
                raise UserError(_("Exception during Bol Instance Creation.\n%s") % str(error))
            return True
        return True

    def create_bol_sales_team(self, name):
        """

        :param name:
        :return:
        """
        crm_team_obj = self.env['crm.team']
        vals = {
            'name': name,
            'use_quotations': True,
            'company_id': self.company_id.id
        }
        return crm_team_obj.create(vals)

    def get_bol_pricelist_id(self):
        """
        This method used to get pricelist for the instance. Creates new pricelist if not found.
        @author: Maulik Barad on Date 13-Feb-2021.
        """
        pricelist_obj = self.env["product.pricelist"]
        price_list_name = self.name + " " + "Pricelist"
        currency_id = self.bol_country_id.currency_id if self.bol_country_id.currency_id else self.env.user.currency_id

        pricelist_id = pricelist_obj.search([("name", "=", price_list_name), ("currency_id", "=", currency_id.id)],
                                            limit=1)
        if not pricelist_id:
            pricelist_id = pricelist_obj.create({"name": price_list_name, "currency_id": currency_id.id})
        return pricelist_id

    def get_bol_fbr_warehouse(self):
        """
        This method used to search warehouse for the instance for FBR Fulfilment.
        @author: Maulik Barad on Date 13-Feb-2021.
        """
        warehouse_id = False
        warehouse_obj = self.env["stock.warehouse"]

        default_warehouse = self.sudo().env.ref("stock.warehouse0")
        if default_warehouse.active:
            if self.company_id == default_warehouse.company_id:
                warehouse_id = default_warehouse.id

        if not warehouse_id:
            warehouse = warehouse_obj.search([("company_id", "=", self.company_id.id), ("is_fbb_warehouse", "=",
                                                                                        False)])
            if warehouse:
                warehouse_id = warehouse[0].id
            else:
                raise UserError(_("FBR Warehouse is not found for %s Company. Please Create a New FBR Warehouse.") %
                                self.company_id.name)

        return warehouse_id

    def get_bol_fbb_warehouse(self):
        """
        This method used to search warehouse for the instance for FBB Fulfilment. Creates new warehouse if not found.
        @author: Maulik Barad on Date 13-Feb-2021.
        """
        warehouse_obj = self.env["stock.warehouse"]

        fbb_warehouse = warehouse_obj.search([("company_id", "=", self.company_id.id),
                                              ("is_fbb_warehouse", "=", True)], limit=1)
        unsaleable_location = self.create_unsellable_location()
        if not fbb_warehouse:
            fbb_warehouse = self.create_fbb_warehouse()
        fbb_warehouse.write({'bol_unsaleable_location_id': unsaleable_location.id})
        return fbb_warehouse.id

    def create_unsellable_location(self):
        stock_location_obj = self.env['stock.location']
        unsellable_location = stock_location_obj.search([('name', '=', self.name + " Unsellable"),
                                                         ('usage', '=', 'internal'),
                                                         ('company_id', '=', self.company_id.id)])
        if not unsellable_location:
            unsellable_vals = {
                'name': self.name + " Unsellable",
                'usage': 'internal',
                'company_id': self.company_id.id,
                'scrap_location': True
            }
            unsellable_location = stock_location_obj.create(unsellable_vals)
        return unsellable_location

    def create_fbb_warehouse(self):
        """
        This method used to Create New FBB Warehouse.
        @author: Maulik Barad on Date 13-Feb-2021.
        """
        partner_obj = self.env["res.partner"]
        stock_warehouse_obj = self.env["stock.warehouse"]

        country = self.bol_country_id
        if self.name:
            if self.name.find(".") != -1:
                name = self.name.rsplit(".", 1)
                code = name[1]
            else:
                code = self.name
        else:
            code = country.code

        vals = {"name": self.name, "country_id": country.id}
        partner = partner_obj.create(vals)

        vals = {
            "name": "FBB %s" % (self.name or country.name),
            "is_fbb_warehouse": True,
            "code": code[:5],
            "company_id": self.company_id.id,
            "partner_id": partner.id
        }
        fbb_warehouse = stock_warehouse_obj.create(vals)
        return fbb_warehouse

    def create_bol_fpos_ept(self, instance):
        account_fpos_obj = self.env['account.fiscal.position']
        vals = {'company_id': instance.company_id.id, 'is_bol_fiscal_position': True}
        countries = [self.env.ref('base.nl'), self.env.ref('base.be')]
        for country in countries:
            fiscal_position = account_fpos_obj.search(
                [('company_id', '=', instance.company_id.id), ('origin_country_ept', '=',
                                                               country.id)])
            if not fiscal_position:
                vals.update({'origin_country_ept': country.id, 'name': "Delivery from %s" % country.name})
                account_fpos_obj.create(vals)

