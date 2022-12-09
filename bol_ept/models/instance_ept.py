# -*- coding: UTF-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
from calendar import monthrange
from datetime import date, datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..bol_api.bol_api import BolAPI

_secondsConverter = {
    'days': lambda interval: interval * 24 * 60 * 60,
    'hours': lambda interval: interval * 60 * 60,
    'weeks': lambda interval: interval * 7 * 24 * 60 * 60,
    'minutes': lambda interval: interval * 60,
}

class BolInstanceEpt(models.Model):
    _name = "bol.instance.ept"
    _description = "Bol Instance"

    def _get_default_shipment_product(self):
        """
        This method sets default shipment product for Bol Instance.
        @author: Maulik Barad on Date 15-Feb-2021.
        """
        shipment_product = self.env.ref('bol_ept.product_product_bol_shipping_ept', False)
        if not shipment_product:
            raise UserError(_("Please upgrade the module and then try to create new instance.\n "
                              "Maybe the shipping product has been deleted "
                              "it will be recreated at the time of module upgrade."))
        return shipment_product

    name = fields.Char()
    company_id = fields.Many2one("res.company", string="Company", help="Bol company")
    bol_fbr_warehouse_id = fields.Many2one('stock.warehouse', 'FBR Warehouse')
    bol_fbb_warehouse_id = fields.Many2one('stock.warehouse', 'FBB Warehouse')
    bol_pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    bol_lang_id = fields.Many2one('res.lang', 'Language')
    client_id = fields.Char()
    secret_id = fields.Text()
    bol_import_order_after_date = fields.Datetime("Import Order After date", help="System will import only "
                                                                                  "those orders which are "
                                                                                  "created after this date.")
    bol_auto_create_product = fields.Boolean('Auto create product?')
    bol_payment_term_id = fields.Many2one('account.payment.term', 'BOL Payment Term')
    is_default_sequence_fbr_sales_order = fields.Boolean("Use Default Odoo Sequence in FBR Sales Orders")
    is_default_sequence_fbb_sales_order = fields.Boolean("Use Default Odoo Sequence in FBB Sales Orders")
    fbr_bol_order_prefix = fields.Char('FBR Bol Order Prefix')
    fbb_bol_order_prefix = fields.Char('FBB Bol Order Prefix')
    bol_auth_token = fields.Text('Auth Token', help="Bol.com authentication token")
    bol_country_id = fields.Many2one("res.country", "Country")
    bol_team_id = fields.Many2one('crm.team', 'Sales Team')
    bol_fulfillment_by = fields.Selection([('FBR', 'FBR'), ('FBB', 'FBB'), ('Both', 'FBR & FBB')],
                                          string='Fulfilment By')
    fbr_auto_workflow_id = fields.Many2one("sale.workflow.process.ept",
                                           string="Auto Workflow (FBR)")
    fbb_auto_workflow_id = fields.Many2one("sale.workflow.process.ept",
                                           string="Auto Workflow (FBB)")
    bol_import_shipment_order_type = fields.Selection([("FBB", "FBB"), ("FBR", "FBR"), ("Both", "FBR & FBB")],
                                                      "Import Shipment for", default="Both")
    stock_field = fields.Selection([("free_qty", "Free Quantity"), ("virtual_available", "Forecast Quantity")],
                                   string="Export Stock Type", default="free_qty")
    active = fields.Boolean(default=True)
    fbb_bol_shipped_page_number = fields.Integer('Last page number of FBB shipments', default=1)
    fbr_bol_shipped_page_number = fields.Integer('Last page number of FBR shipments', default=1)
    shipment_charge_product_id = fields.Many2one("product.product", "Shipment Fee",
                                                 domain=[('type', '=', 'service')],
                                                 default=_get_default_shipment_product)
    inventory_last_sync_on = fields.Datetime(string="Last stock export date",
                                             help="Last stock export date'")
    auto_validate_inventory = fields.Boolean(default=False)
    state = fields.Selection([('not_confirmed', 'Not Confirmed'), ('confirmed', 'Confirmed')],
                             default='not_confirmed')
    is_bol_create_schedule = fields.Boolean("Create Schedule Activity ? ", default=False,
                                            help="If checked, Then Schedule Activity create on order data queues"
                                                 " will any queue line failed.")
    bol_user_ids = fields.Many2many("res.users", "bol_instance_res_users_rel",
                                    "bol_instance_id", "res_users_id", string="Responsible User")
    bol_activity_type_id = fields.Many2one("mail.activity.type", string="Bol Activity Type")
    bol_date_deadline = fields.Integer("Deadline Lead Days for Bol", default=1,
                                       help="its add number of  days in schedule activity deadline date ")
    #Below field used for kanban view
    color = fields.Integer(string='Color Index')
    bol_kanban_order_data = fields.Text(compute="_compute_kanban_bol_order_data")

    #Below field used for onboarding Panel
    is_instance_create_from_onboarding_panel = fields.Boolean(default=False)
    is_onboarding_configurations_done = fields.Boolean(default=False)

    def _compute_kanban_bol_order_data(self):
        """This method used to prepare a data for the instance dashboard.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 26/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        context = dict(self.env.context)
        if not self._context.get('sort') :
            context.update({'sort': 'week'})
        if not self._context.get('fulfillment_by'):
            context.update({'fulfillment_by': 'Both'})
        self.env.context = context
        for record in self:
            #Prepare where clause for fulfillment by as per selected
            fulfillment_by_where_clause = self.prepare_fulfillment_by_where_clause(record)
            # Prepare values for Graph
            values = self.get_graph_data(record, fulfillment_by_where_clause)
            data_type, comparison_value = self.get_compare_data(record, fulfillment_by_where_clause)
            # Total sales
            total_sales = round(sum([key['y'] for key in values]), 2)
            # Order count query
            fbr_order_data = self.get_fbr_total_orders(record, fulfillment_by_where_clause)
            fbb_order_data = self.get_fbb_total_orders(record, fulfillment_by_where_clause)
            # Product count query
            product_data = self.get_total_products(record)
            record.bol_kanban_order_data = json.dumps({
                "values": values,
                "title": "",
                "key": "Order: Untaxed amount",
                "area": True,
                "color": "#875A7B",
                "is_sample_data": False,
                "total_sales": total_sales,
                "fbr_order_data": fbr_order_data,
                "fbb_order_data": fbb_order_data,
                "product_date": product_data,
                "sort_on": self._context.get('sort'),
                "fulfillment_by": self._context.get('fulfillment_by'),
                "currency_symbol": record.company_id.currency_id.symbol or '',
                "graph_sale_percentage": {'type': data_type, 'value': comparison_value}
            })

    @staticmethod
    def prepare_fulfillment_by_where_clause(record):
        """This method use for the prepare fulfillment by where clause.
            @return: where clause string
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        if record._context.get('fulfillment_by') == 'FBR':
            fulfillment_where_clause = """AND bol_fulfillment_by = 'FBR'"""
        elif record._context.get('fulfillment_by') == 'FBB':
            fulfillment_where_clause = """AND bol_fulfillment_by = 'FBB'"""
        else:
            fulfillment_where_clause = """AND bol_fulfillment_by in ('FBR', 'FBB')"""
        return fulfillment_where_clause

    @staticmethod
    def get_graph_data(record, fulfillment_by_where_clause):
        """This method use to get the details of sale orders and total amount month wise or year wise to prepare the graph.
            @return: sale order date or month and sum of sale orders amount of current instance
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """

        def get_current_week_date(record, fulfillment_by_where_clause):
            record._cr.execute("""SELECT to_char(date(d.day),'DAY'), t.amount_untaxed as sum
                                FROM  (
                                   SELECT day
                                   FROM generate_series(date(date_trunc('week', (current_date)))
                                    , date(date_trunc('week', (current_date)) + interval '6 days')
                                    , interval  '1 day') day
                                   ) d
                                LEFT   JOIN 
                                (SELECT date(date_order)::date AS day, sum(amount_untaxed) as amount_untaxed
                                   FROM   sale_order
                                   WHERE  date(date_order) >= (select date_trunc('week', date(current_date)))
                                   AND    date(date_order) <= (select date_trunc('week', date(current_date)) 
                                   + interval '6 days')
                                   AND bol_instance_id={0} and state in ('sale','done') {1}
                                   GROUP  BY 1
                                   ) t USING (day)
                                ORDER  BY day""" .format(record.id, fulfillment_by_where_clause)
                                    )
            return record._cr.dictfetchall()

        def graph_of_current_month(record, fulfillment_by_where_clause):
            record._cr.execute("""select EXTRACT(DAY from date(date_day)) :: integer,sum(amount_untaxed) from (
                        SELECT 
                          day::date as date_day,
                          0 as amount_untaxed
                        FROM generate_series(date(date_trunc('month', (current_date)))
                            , date(date_trunc('month', (current_date)) + interval '1 MONTH - 1 day')
                            , interval  '1 day') day
                        union all
                        SELECT date(date_order)::date AS date_day,
                        sum(amount_untaxed) as amount_untaxed
                          FROM   sale_order
                        WHERE  date(date_order) >= (select date_trunc('month', date(current_date)))
                        AND date(date_order)::date <= (select date_trunc('month', date(current_date)) 
                        + '1 MONTH - 1 day')
                        and bol_instance_id = {0} and state in ('sale','done') {1}
                        group by 1
                        )foo 
                        GROUP  BY 1
                        ORDER  BY 1""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def graph_of_current_year(record, fulfillment_by_where_clause):
            record._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',month),'MONTH')),sum(amount_untaxed) from
                                (SELECT DATE_TRUNC('month',date(day)) as month,
                                  0 as amount_untaxed
                                FROM generate_series(date(date_trunc('year', (current_date)))
                                , date(date_trunc('year', (current_date)) + interval '1 YEAR - 1 day')
                                , interval  '1 MONTH') day
                                union all
                                SELECT DATE_TRUNC('month',date(date_order)) as month,
                                sum(amount_untaxed) as amount_untaxed
                                  FROM   sale_order
                                WHERE  date(date_order) >= (select date_trunc('year', date(current_date))) AND 
                                date(date_order)::date <= (select date_trunc('year', date(current_date)) 
                                + '1 YEAR - 1 day')
                                and bol_instance_id = {0} and state in ('sale','done') {1}
                                group by DATE_TRUNC('month',date(date_order))
                                order by month
                                )foo 
                                GROUP  BY foo.month
                                order by foo.month""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def graph_of_all_time(record, fulfillment_by_where_clause):
            record._cr.execute("""select TRIM(TO_CHAR(DATE_TRUNC('month',date_order),'YYYY-MM')),sum(amount_untaxed)
                                from sale_order where bol_instance_id = {0} and state in ('sale','done') {1}
                                group by DATE_TRUNC('month',date_order) 
                                order by DATE_TRUNC('month',date_order)""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        # Prepare values for Graph
        if record._context.get('sort') == 'week':
            result = get_current_week_date(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "month":
            result = graph_of_current_month(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "year":
            result = graph_of_current_year(record, fulfillment_by_where_clause)
        else:
            result = graph_of_all_time(record, fulfillment_by_where_clause)
        values = [{"x": ("{}".format(data.get(list(data.keys())[0]))), "y": data.get('sum') or 0.0} for data in result]
        return values

    @staticmethod
    def get_compare_data(record, fulfillment_by_where_clause):
        """This method use the prepare data of Comparison ratio of orders (weekly,monthly and yearly based on selection).
            @return: Comparison ratio of orders (weekly,monthly and yearly based on selection)
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        data_type = False
        total_percentage = 0.0

        def get_compared_week_data(record, fulfillment_by_where_clause):
            current_total = 0.0
            previous_total = 0.0
            day_of_week = date.weekday(date.today())
            record._cr.execute("""select sum(amount_untaxed) as current_week from sale_order
                                where date(date_order) >= (select date_trunc('week', date(current_date))) and
                                bol_instance_id={0} and state in ('sale','done') {1}""" .format(record.id,
                                                                                          fulfillment_by_where_clause))
            current_week_data = record._cr.dictfetchone()
            if current_week_data:
                current_total = current_week_data.get('current_week') if current_week_data.get('current_week') else 0
            # Previous week data
            record._cr.execute("""select sum(amount_untaxed) as previous_week from sale_order
                            where date(date_order) between (select date_trunc('week', current_date) - interval '7 day') 
                            and (select date_trunc('week', (select date_trunc('week', current_date) - interval '7
                            day')) + interval '{0} day')
                            and bol_instance_id={1} and state in ('sale','done') {2}
                            """ .format(day_of_week, record.id,fulfillment_by_where_clause))

            previous_week_data = record._cr.dictfetchone()
            if previous_week_data:
                previous_total = previous_week_data.get('previous_week') if previous_week_data.get(
                    'previous_week') else 0
            return current_total, previous_total

        def get_compared_month_data(record, fulfillment_by_where_clause):
            current_total = 0.0
            previous_total = 0.0
            day_of_month = date.today().day - 1
            record._cr.execute("""select sum(amount_untaxed) as current_month from sale_order
                                where date(date_order) >= (select date_trunc('month', date(current_date)))
                                and bol_instance_id={0} and state in ('sale','done') {1}""".format(record.id,
                                                                                                   fulfillment_by_where_clause))
            current_data = record._cr.dictfetchone()
            current_total = current_data.get('current_month') if current_data and current_data.get('current_month') else 0
            # Previous week data
            record._cr.execute("""select sum(amount_untaxed) as previous_month from sale_order where date(date_order)
                            between (select date_trunc('month', current_date) - interval '1 month') and
                            (select date_trunc('month', (select date_trunc('month', current_date) - interval
                            '1 month')) + interval '{0} days')
                            and bol_instance_id={1} and state in ('sale','done') {2}
                            """ .format(day_of_month, record.id,fulfillment_by_where_clause))
            previous_data = record._cr.dictfetchone()
            previous_total = previous_data.get('previous_month') if previous_data and previous_data.get('previous_month') else 0
            return current_total, previous_total

        def get_compared_year_data(record, fulfillment_by_where_clause):
            current_total = 0.0
            previous_total = 0.0
            year_begin = date.today().replace(month=1, day=1)
            year_end = date.today()
            delta = (year_end - year_begin).days - 1
            record._cr.execute("""select sum(amount_untaxed) as current_year from sale_order
                                where date(date_order) >= (select date_trunc('year', date(current_date)))
                                and bol_instance_id={0} and state in ('sale','done') {1}""" .format(record.id,
                                                                                               fulfillment_by_where_clause))
            current_data = record._cr.dictfetchone()
            current_total = current_data.get('current_year') if current_data and current_data.get('current_year') else 0
            # Previous week data
            record._cr.execute("""select sum(amount_untaxed) as previous_year from sale_order where date(date_order)
                            between (select date_trunc('year', date(current_date) - interval '1 year')) and 
                            (select date_trunc('year', date(current_date) - interval '1 year') + interval '{0} days') 
                            and bol_instance_id={1} and state in ('sale','done') {2}
                            """ .format(delta, record.id,fulfillment_by_where_clause))

            previous_data = record._cr.dictfetchone()
            if previous_data:
                previous_total = previous_data.get('previous_year') if previous_data.get('previous_year') else 0
            return current_total, previous_total

        if record._context.get('sort') == 'week':
            current_total, previous_total = get_compared_week_data(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "month":
            current_total, previous_total = get_compared_month_data(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "year":
            current_total, previous_total = get_compared_year_data(record, fulfillment_by_where_clause)
        else:
            current_total, previous_total = 0.0, 0.0
        if current_total > 0.0:
            if current_total >= previous_total:
                data_type = 'positive'
                total_percentage = (current_total - previous_total) * 100 / current_total
            if previous_total > current_total:
                data_type = 'negative'
                total_percentage = (previous_total - current_total) * 100 / current_total
        return data_type, round(total_percentage, 2)

    @staticmethod
    def get_fbr_total_orders(record, fulfillment_by_where_clause):
        """This method use the prepare data of FBR orders.
            @return: list of dict with FBR data
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        def orders_of_current_week(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order)
                                >= (select date_trunc('week', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBR' {1}
                                order by date(date_order)
                        """  .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_current_month(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('month', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBR' {1}
                                order by date(date_order)
                        """ .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_current_year(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('year', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBR' {1}
                                order by date(date_order)"""
                            .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_all_time(record, fulfillment_by_where_clause):
            record._cr.execute(
                """select id from sale_order where bol_instance_id = {0} and state in ('sale','done') and 
                bol_fulfillment_by = 'FBR' {1}""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        order_data = {}
        if record._context.get('sort') == "week":
            result = orders_of_current_week(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "month":
            result = orders_of_current_month(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "year":
            result = orders_of_current_year(record, fulfillment_by_where_clause)
        else:
            result = orders_of_all_time(record, fulfillment_by_where_clause)
        order_ids = [data.get('id') for data in result]
        view = record.env.ref('bol_ept.action_bol_fbr_sales_order_only').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    @staticmethod
    def get_fbb_total_orders(record, fulfillment_by_where_clause):
        """This method use the prepare data of FBB orders.
            @return: list of dict with FBB data
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        def orders_of_current_week(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order)
                                >= (select date_trunc('week', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBB' {1}
                                order by date(date_order)""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_current_month(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('month', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBB' {1}
                                order by date(date_order)""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_current_year(record, fulfillment_by_where_clause):
            record._cr.execute("""select id from sale_order where date(date_order) >=
                                (select date_trunc('year', date(current_date)))
                                and bol_instance_id= {0} and state in ('sale','done') and bol_fulfillment_by = 'FBB' {1}
                                order by date(date_order)""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        def orders_of_all_time(record, fulfillment_by_where_clause):
            record._cr.execute(
                """select id from sale_order where bol_instance_id = {0} and state in ('sale','done') and 
                bol_fulfillment_by = 'FBB' {1}""" .format(record.id, fulfillment_by_where_clause))
            return record._cr.dictfetchall()

        order_data = {}
        if record._context.get('sort') == "week":
            result = orders_of_current_week(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "month":
            result = orders_of_current_month(record, fulfillment_by_where_clause)
        elif record._context.get('sort') == "year":
            result = orders_of_current_year(record, fulfillment_by_where_clause)
        else:
            result = orders_of_all_time(record, fulfillment_by_where_clause)
        order_ids = [data.get('id') for data in result]
        view = record.env.ref('bol_ept.action_bol_fbb_sales_order_only').sudo().read()[0]
        action = record.prepare_action(view, [('id', 'in', order_ids)])
        order_data.update({'order_count': len(order_ids), 'order_action': action})
        return order_data

    @staticmethod
    def get_total_products(record):
        """This method is used to prepare list of products which exported in BOl.com.
            @return: total number of Bol products ids and action for products
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        product_data = {}
        record._cr.execute("""select count(id) as total_count from bol_offer_ept where
                        exported_in_bol = True and bol_instance_id = %s""" % record.id)
        result = record._cr.dictfetchall()
        if result:
            total_count = result[0].get('total_count')
        view = record.env.ref('bol_ept.action_bol_offer_ept').sudo().read()[0]
        action = record.prepare_action(view, [('exported_in_bol', '=', True), ('bol_instance_id', '=', record.id)])
        product_data.update({'product_count': total_count, 'product_action': action})
        return product_data

    def prepare_action(self, view, domain):
        """This method is used to action dictionary to redirect appropriate view.
            @return: action
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        action = {
            'name': view.get('name'),
            'type': view.get('type'),
            'domain': domain,
            'view_mode': view.get('view_mode'),
            'view_id': view.get('view_id')[0] if view.get('view_id') else False,
            'views': view.get('views'),
            'res_model': view.get('res_model'),
            'target': view.get('target'),
        }
        if 'tree' in action['views'][0]:
            action['views'][0] = (action['view_id'], 'list')
        return action

    @api.model
    def perform_operation(self, record_id):
        """This method is used to prepare bol operation action.
            @return: action
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        view = self.env.ref('bol_ept.action_wizard_bol_instance_import_export_operations').sudo().read()[0]
        action = self.prepare_action(view, [])
        action.update({'context': {'default_instance_id': record_id}})
        return action

    @api.model
    def open_report(self, record_id):
        """This method is used to prepare bol report action.
            @return: action
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        view = self.env.ref('bol_ept.bol_sale_report_action_dashboard').sudo().read()[0]
        action = self.prepare_action(view, [('bol_instance_id', '=', record_id)])
        action.update({'context': {'search_default_bol_instances': record_id, 'search_default_Sales': 1,
                                   'search_default_filter_date': 1}})
        return action

    @api.model
    def open_logs(self, record_id):
        """This method is used to prepare bol log action.
            @return: action
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29/05/2021.
            Task Id : 173987 - Bol.com Dashboard
        """
        view = self.env.ref('bol_ept.action_bol_common_log_book_ept').sudo().read()[0]
        return self.prepare_action(view, [('bol_instance_id', '=', record_id)])

    def get_bol_token(self):
        """
        This method is used to generate the Bol Auth Token.
        @author: Maulik Barad on Date 15-Feb-2021.
        """
        try:
            result = BolAPI.get_bol_token(self.client_id, self.secret_id)
            if not result.get("access_token"):
                raise UserError(_("Given Credentials are incorrect, please provide Correct Credentials."))
            self.write({'bol_auth_token': 'Bearer ' + result.get('access_token')})
            self._cr.commit()
        except Exception as error:
            raise UserError(_("Something went wrong.\n%s") % str(error))

        return True

    def test_bol_connection(self):
        """
        This method is used to Test Bol.com Connection
        :return: Raise error if connection is not established with Bol.com
        @author: Ekta Bhut, 15th March 2021
        """
        # This method needs to remove
        result = BolAPI.get_bol_token(self.client_id, self.secret_id)
        if result.get('access_token'):
            self.write({'state': 'confirmed', 'bol_auth_token': 'Bearer ' + result.get('access_token')})
            self._cr.commit()
            raise UserError(_('Service Working Properly.'))
        raise UserError(_('Given Credential is incorrect, please provide correct Credential'))

    def reset_to_confirm(self):
        """
        Used to reset Bol.com Instance
        :return: True
        @author: Ekta Bhut, 15th March 2021
        """
        self.write({'state': 'not_confirmed'})
        return True

    def confirm(self):
        """
        Used to Confirm Bol.com Instance
        :return:
        @author: Ekta Bhut, 15th March 2021
        """
        try:
            result = BolAPI.get_bol_token(self.client_id, self.secret_id)
            if result.get('access_token'):
                self.write({'state': 'confirmed'})
            else:
                raise UserError(
                    _('Given Credential is incorrect, please provide correct Credential. \nResponse: %s' %result))
        except Exception as e:
            raise UserError(_('Given Credential is incorrect, please provide correct Credential. '
                              '\nError: %s' % (e)))
        return True

    def toggle_active(self):
        """
        Inverse the value of the field ``active`` on the records in ``self``.
        :return: True
        @author: Ekta Bhut, 15th March 2021
        """
        for record in self:
            record.active = not record.active

    def get_bol_instance_fulfillment_by(self):
        """
        This method is used to get Fulfillment by of Bol Instance
        :return: List of Fulfillment by
        @author : Ekta Bhut
        """
        fulfillment_by = []
        if self.bol_fulfillment_by == 'FBR':
            fulfillment_by.append('FBR')
        if self.bol_fulfillment_by == 'FBB':
            fulfillment_by.append('FBB')
        if self.bol_fulfillment_by == 'Both':
            fulfillment_by = ['FBR', 'FBB']
        return fulfillment_by

    def get_bol_warehouse_ids(self):
        """
        This method is used to get Warehouse of Bol instance
        :return: List of FBR and FBB warehouses
        @author : Ekta Bhut
        """
        warehouse_ids = self.env['stock.warehouse']
        if self.bol_fulfillment_by == 'FBR':
            warehouse_ids += self.bol_fbr_warehouse_id
        if self.bol_fulfillment_by == 'FBB':
            warehouse_ids += self.bol_fbb_warehouse_id
        if self.bol_fulfillment_by == 'Both':
            warehouse_ids += self.bol_fbb_warehouse_id
            warehouse_ids += self.bol_fbr_warehouse_id
        return warehouse_ids

    def list_of_instance_cron(self):
        """
        This methos used to list out activated schedulars.
        :return: Schedular Action
        @author : Ekta Bhut
        """
        bol_instance_cron = self.env['ir.cron'].sudo().search([('bol_instance_cron_id', '=', self.id)])
        action = {
            'domain': "[('id', 'in', " + str(bol_instance_cron.ids) + " )]",
            'name': 'Cron Scheduler',
            'view_mode': 'tree,form',
            'res_model': 'ir.cron',
            'type': 'ir.actions.act_window',
        }
        return action

    def global_cron_configuration_action(self):
        """
        Open Global cron configuration wizard
        :return: action
        """
        action = self.env.ref('bol_ept.action_wizard_for_open_fbr_and_fbb_cron_configuration').read()[0]
        context = {
            'bol_instance_id': self.id,
            'bol_fulfillment_by': self.bol_fulfillment_by
        }
        action['context'] = context
        return action

    def fbb_cron_configuration_action(self):
        """
        Open FBB cron configuration wizard
        :return: action
        """
        action = self.env.ref('bol_ept.action_wizard_for_open_fbb_cron_configuration').read()[0]
        context = {
            'bol_instance_id': self.id,
            'bol_fulfillment_by': self.bol_fulfillment_by
        }
        action['context'] = context
        return action

    def fbr_cron_configuration_action(self):
        """
        Open FBR cron configuration wizard
        :return: action
        """
        action = self.env.ref('bol_ept.action_wizard_for_open_fbr_cron_configuration').read()[0]
        context = {
            'bol_instance_id': self.id,
            'bol_fulfillment_by': self.bol_fulfillment_by
        }
        action['context'] = context
        return action

    def get_bol_cron_execution_time(self, cron_name):
        """
        This method is used to get the interval time of the cron.
        @param cron_name: External ID of the Cron.
        @return: Interval time in seconds.
        @author: Ekta Bhut
        """
        process_queue_cron = self.env.ref(cron_name, False)
        if not process_queue_cron:
            raise UserError(_("Please upgrade the module. \n Maybe the job has been deleted, it will be recreated at "
                              "the time of module upgrade."))
        interval = process_queue_cron.interval_number
        interval_type = process_queue_cron.interval_type
        if interval_type == "months":
            days = 0
            current_year = fields.Date.today().year
            current_month = fields.Date.today().month
            for i in range(0, interval):
                month = current_month + i
                if month > 12:
                    if month == 13:
                        current_year += 1
                    month -= 12

                days_in_month = monthrange(current_year, month)[1]
                days += days_in_month

            interval_type = "days"
            interval = days
        interval_in_seconds = _secondsConverter[interval_type](interval)
        return interval_in_seconds

    def search_bol_instance(self):
        """ This method used to search the bol instance.
            @return: Record of bol instance
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 June 2021 .
            Task_id: 175221 - BOl.com panel
        """
        company = self.env.company or self.env.user.company_id
        instance = self.search(
            [('is_instance_create_from_onboarding_panel', '=', True),
             ('is_onboarding_configurations_done', '=', False),
             ('company_id', '=', company.id)], limit=1, order='id desc')
        if not instance:
            instance = self.search([('company_id', '=', company.id),
                                    ('is_onboarding_configurations_done', '=', False)],
                                   limit=1, order='id desc')
            instance.write({'is_instance_create_from_onboarding_panel': True})
        return instance
