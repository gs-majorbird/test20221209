# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    # App information
    'name': 'Odoo Bol.com Connector',
    'version': '14.0.3.0.1',
    'category': 'Sales',
    'license': 'OPL-1',
    'summary': "Odoo Bol.com integration helps to manage key operations of Bol.com efficiently from Odoo.Customers can manage their orders, can check the reporting, & other operations as mentioned in the User documentation.Apart from Odoo Walmart Connector, we do have other ecommerce solutions or applications such as Woocommerce connector , Shopify connector , magento connector and also we have solutions for Marketplace Integration such as Odoo Amazon connector , Odoo eBay connector , Odoo walmart Connector.Aside from ecommerce integration and ecommerce marketplace integration, we also provide solutions for various operations, such as shipping , logistics , shipping labels , and shipping carrier management with our shipping integration , known as the Shipstation connector.For the customers who are into Dropship business, we do provide EDI Integration that can help them manage their Dropshipping business with our Dropshipping integration or Dropshipper integration It is listed as Dropshipping EDI integration and Dropshipper EDI integration.Emipro applications can be searched with different keywords like Amazon integration , Shopify integration , Woocommerce integration, Magento integration , Amazon vendor center module , Amazon seller center module , Inter company transfer , eBay integration , Bol.com integration , inventory management , warehouse transfer module , dropship and dropshipper integration and other Odoo integration application or module",

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',

    # Dependencies
    'depends': ['common_connector_library'],
    # Views
    'data': [
        "security/group.xml",
        "security/ir.model.access.csv",
        "data/product_data.xml",
        "data/bol.delivery.carrier.code.ept.csv",
        "views/main_menu.xml",
        "views/sequence.xml",
        "wizard/instance_config_ept.xml",
        "wizard/res_config_settings.xml",
        "views/view_sale_order.xml",
        "views/view_bol_offer_ept.xml",
        "views/view_bol_product_sync_report.xml",
        "views/view_delivery_carrier_code_ept.xml",
        "wizard/prepare_product_for_export.xml",
        "wizard/process_import_export_ept.xml",
        "report/view_sale_report.xml",
        "views/view_bol_order_queue_ept.xml",
        "views/view_bol_order_queue_line_ept.xml",
        "views/view_shipped_order_queue_ept.xml",
        "views/view_shipped_order_data_queue_line_ept.xml",
        "views/view_stock_picking.xml",
        "views/view_account_move.xml",
        "views/view_stock_warehouse.xml",
        "views/view_stock_inventory.xml",
        "wizard/view_cron_configuration_ept.xml",
        "views/view_common_log_book.xml",
        "views/view_auto_workflow_process.xml",
        "data/ir_cron.xml",
        "views/assets.xml",
        "views/onboarding_panel_view.xml",
        "wizard/onboarding_instance_configuration_wizard.xml",
        "wizard/basic_configuration_onboarding.xml",
        "views/instance_view.xml",
        "wizard/bol_onboarding_confirmation_ept_view.xml"
    ],

    # Odoo Store Specific

    'images': ['static/description/cover.jpg'],
    'qweb': ['static/src/xml/dashboard_widget_inherit.xml'],
    # Technical
    'installable': True,
    'currency': 'EUR',
    'price': 579.00,
    'live_test_url': 'http://www.emiprotechnologies.com/free-trial?app=bol-ept&version=14',
    'auto_install': False,
    'application': True,
}
