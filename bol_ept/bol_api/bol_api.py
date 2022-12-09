# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import json
import requests

_parameters = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "grant_type": "client_credentials"
}
#
# headers = {
#     "Accept": "application/vnd.retailer.v4+json",
#     "Content-Type": "application/vnd.retailer.v4+json",
# }
headers = {
    "Accept": "application/vnd.retailer.v8+json",
    "Content-Type": "application/vnd.retailer.v8+json",
}

csv_headers = {
    "Accept": "application/vnd.retailer.v8+csv",
    "Content-Type": "application/x-www-form-urlencoded",
}

_api_endpoints = {
    # GET Endpoints.
    "token": "https://login.bol.com/token",
    "orders": "https://api.bol.com/retailer/orders?",
    "returns_orders": "https://api.bol.com/retailer/returns?",
    "single_order": "https://api.bol.com/retailer/orders/",
    "transporter": "https://api.bol.com/retailer/inbounds/fbb-transporters",
    "process_status": "https://api.bol.com/shared/process-status/",
    "delivery_windows": "https://api.bol.com/retailer/inbounds/delivery-windows?",
    "packing_shipment_label": "https://api.bol.com/retailer/inbounds/",
    "inbound_shipment_list": "https://api.bol.com/retailer/inbounds?page=",
    "offer_file": "https://api.bol.com/retailer/offers/export/",
    "offer": "https://api.bol.com/retailer/offers/",
    "shipment_list": "https://api.bol.com/retailer/shipments?",
    "single_shipment_list": "https://api.bol.com/retailer/shipments/",

    "inventory": "https://api.bol.com/retailer/inventory?",

    "shipment_status": "https://api.bol.com/shared/process-status?",

    # POST Endpoints.
    "export_offer_file": "https://api.bol.com/retailer/offers/export",
    "create_shipment": "https://api.bol.com/retailer/inbounds",
    "product_label": "https://api.bol.com/retailer/inbounds/productlabels",
    "new_offer": "https://api.bol.com/retailer/offers",

    # PUT Endpoints.
    "ship_order_item": "https://api.bol.com/retailer/orders/",
    "transport_info": "https://api.bol.com/retailer/transports/",
    "handled_returns": "https://api.bol.com/retailer/returns/",
    "update_order_status" : "https://api.bol.com/retailer/orders/shipment",

}


class BolAPI:

    @staticmethod
    def get_bol_token(client_id, client_secret_key):
        data = {
            "Content-Type": _parameters["Content-Type"],
            "client_id": client_id,
            "client_secret": client_secret_key,
            "Accept": _parameters["Accept"],
            "grant_type": _parameters["grant_type"]
        }
        response = requests.post(url=_api_endpoints.get("token"), data=data)
        return response.json()

    @staticmethod
    def get(endpoint, bol_token, query_string=""):
        """
        This method is used to make the Get request for all process of Bol.com.
        @param endpoint: Endpoint (Key to fetch endpoint from _endpoints dict).
        @param bol_token: Bol Auth Token.
        @param query_string: Query string to attach additional parameters.
        @return: 1) Response, 2) Response in JSON format.
        @author: Maulik Barad on Date 16-Feb-2021.
        """
        url = _api_endpoints.get(endpoint) + query_string
        headers.update(Authorization=bol_token)

        response = requests.get(url, headers=headers)
        return response, response.json()

    @staticmethod
    def get_csv(endpoint, bol_token, query_string=""):
        """
        This method is used to make the Get request for all process of Bol.com.
        @param endpoint: Endpoint (Key to fetch endpoint from _endpoints dict).
        @param bol_token: Bol Auth Token.
        @param query_string: Query string to attach additional parameters.
        @return: 1) Response, 2) Response in JSON format.
        @author: Maulik Barad on Date 16-Feb-2021.
        """
        url = _api_endpoints.get(endpoint) + query_string
        csv_headers.update(Authorization=bol_token)

        response = requests.get(url, headers=csv_headers)
        return response, response.text

    @staticmethod
    def post(endpoint, bol_token, payload):
        """
        This method is used to make the Post request for all process of Bol.com.
        @param endpoint: Endpoint (Key to fetch endpoint from _endpoints dict).
        @param bol_token: Bol Auth Token.
        @param payload: Data to pass with request.
        @return: 1) Response, 2) Response in JSON format.
        @author: Maulik Barad on Date 16-Feb-2021.
        """
        url = _api_endpoints.get(endpoint)
        headers.update(Authorization=bol_token)

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response, response.json()

    @staticmethod
    def put(endpoint, bol_token, query_string="", payload=False):
        """
        This method is used to make the Put request for all process of Bol.com.
        @param endpoint: Endpoint (Key to fetch endpoint from _endpoints dict).
        @param bol_token: Bol Auth Token.
        @param query_string: Query string to attach additional parameters.
        @param payload: Data to pass with request.
        @return: 1) Response, 2) Response in JSON format.
        @author: Maulik Barad on Date 16-Feb-2021.
        """
        if not payload:
            payload = {}
        url = _api_endpoints.get(endpoint) + query_string
        headers.update(Authorization=bol_token)

        response = requests.put(url, headers=headers, data=json.dumps(payload))
        return response, response.json()

    @staticmethod
    def delete(endpoint, bol_token, query_string=""):
        """
        This method is used to make the Delete request for all process of Bol.com.
        @param endpoint: Endpoint (Key to fetch endpoint from _endpoints dict).
        @param bol_token: Bol Auth Token.
        @param query_string: Query string to attach additional parameters.
        @return: 1) Response, 2) Response in JSON format.
        @author: Maulik Barad on Date 16-Feb-2021.
        """
        url = _api_endpoints.get(endpoint) + query_string
        headers.update(Authorization=bol_token)

        response = requests.delete(url, headers=headers)
        return response, response.json()

    # def get_bol_orders(self, bol_token):
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", _api_endpoints.get("orders"), headers=headers, data=payload)
    #     return response.json()

    # def get_bol_open_orders(self, fulfilment_by, page, bol_token):
    #     url = _api_endpoints.get("get_all_open_orders") + "fulfilment-method=" + fulfilment_by + "&" + "page=" + str(
    #         page)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def get_all_returns_orders(self, page, handled, fulfilment_by, bol_token):
    #     url = _api_endpoints.get("get_all_returns_orders") + "page=" + str(page) + "&handled=" + \
    #           str(handled) + "&fulfilment-method=" + fulfilment_by
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def get_single_order(self, bol_token, order_id):
    #     url = _api_endpoints.get("get_single_order") + str(order_id)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def getUnhandled(self, bol_token, page):
    #     url = _api_endpoints.get("get_unhandled_returns") + "page=" + str(page) + "&" + "handled=false"
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def getFbbTransports(self, bol_token):
    #     url = _api_endpoints.get("get_transporter")
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getProcessStatus(self, bol_token, process_status_id):
    #     url = _api_endpoints.get("process_status") + str(process_status_id)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def getDeliveryWindows(self, bol_token, delivery_date, item_to_send):
    #     url = _api_endpoints.get("get_delivery_windows") + str(delivery_date) + "&items-to-send=" + str(item_to_send)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def getShippingLabel(self, bol_token, bol_inbound_id):
    #     url = _api_endpoints.get("get_shipping_label") + str(bol_inbound_id) + "/shippinglabel"
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+pdf",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.text

    # def getPackingList(self, bol_token, bol_inbound_id):
    #     url = _api_endpoints.get("get_packing_list") + str(bol_inbound_id) + "/packinglist"
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+pdf",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.text

    # def getInboundShipment(self, bol_token, bol_inbound_id):
    #     url = _api_endpoints.get("get_inbound_shipment") + str(bol_inbound_id)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getInboundShipmentList(self, bol_token, page):
    #     url = _api_endpoints.get("get_inbound_shipment_list") + str(page)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token}
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getOffersFile(self, bol_token, enitity_id):
    #     url = _api_endpoints.get("get_offer_file") + enitity_id
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+csv",
    #         "Content-Type": "application/x-www-form-urlencoded",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.text

    # def getSingleOffer(self, bol_token, offerid):
    #     url = _api_endpoints.get("get_single_offer") + offerid
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def getShipmentList(self, bol_token, fulfilment_method, page):
    #     url = _api_endpoints.get("get_shipment_list") + fulfilment_method + "&page=" + str(page)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getSingleOrderShipmentList(self, bol_token, order_id):
    #     url = _api_endpoints.get("get_single_order_shipment_list") + "order-id=" + str(order_id)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getSingleShipment(self, bol_token, shipment_id):
    #     url = _api_endpoints.get("get_single_shipment_list") + str(shipment_id)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getLvbFbbInventory(self, bol_token, page):
    #     url = _api_endpoints.get("get_inventory") + str(page)
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("GET", url, headers=headers, data=payload)
    #     return response, response.json()

    # def request_offer_export_file(self, bol_token):
    #     url = "https://api.bol.com/retailer/offers/export"
    #     payload = {"format": "CSV"}
    #     content_type = "application/vnd.retailer.v3+json"
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": content_type,
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("POST", url, headers=headers, data=json.dumps(payload), allow_redirects=False)
    #     return response, response.json()

    # def createShipment(self, bol_token, payload):
    #     url = _api_endpoints.get("create_shipment")
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token}
    #     response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getProductLabel(self, bol_token, payload):
    #     url = _api_endpoints.get("get_product_label")
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+pdf",
    #         "Content-Type": "multipart/form-data",
    #         "Authorization": bol_token}
    #     response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    #     return response, response.text

    # def createNewOffer(self, bol_token, payload):
    #     url = _api_endpoints.get("create_new_offer")
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def shipOrderItem(self, bol_token, order_item_id):
    #     url = _api_endpoints.get("ship_order_item") + str(order_item_id) + "/shipment"
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=payload)
    #     return response, response.json()

    # def shipOrderItemWithTrackingInfo(self, bol_token, order_item_id, payload):
    #     url = _api_endpoints.get("ship_order_item_with_tracking_info") + str(order_item_id) + "/shipment"
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def updateTransportInfo(self, bol_token, transport_id, payload):
    #     url = _api_endpoints.get("update_transport_info") + str(transport_id)
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def getHandled(self, bol_token, rmaId, payload):
    #     url = _api_endpoints.get("get_handled_returns") + str(rmaId)
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def updateProductStock(self, bol_token, offer_id, payload):
    #     url = _api_endpoints.get("update_product_stock") + offer_id + "/stock"
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def updateProductPrice(self, bol_token, offer_id, payload):
    #     url = _api_endpoints.get("update_product_price") + offer_id + "/price"
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def updateOffer(self, bol_token, offer_id, payload):
    #     url = _api_endpoints.get("update_offer") + offer_id
    #     headers = {
    #         "Accept": "application/json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("PUT", url, headers=headers, data=json.dumps(payload))
    #     return response, response.json()

    # def deleteSingleOffer(self, bol_token, offerid):
    #     url = _api_endpoints.get("delete_single_offer") + offerid
    #     payload = {}
    #     headers = {
    #         "Accept": "application/vnd.retailer.v3+json",
    #         "Content-Type": "application/vnd.retailer.v3+json",
    #         "Authorization": bol_token
    #     }
    #     response = requests.request("DELETE", url, headers=headers, data=payload)
    #     return response, response.json()

# _api_endpoints = {
#     'token': "https://login.bol.com/token",
#     'orders': "https://api.bol.com/retailer/orders?fulfilment-method=FBR",
#     'get_all_open_orders': "https://api.bol.com/retailer/orders?",
#     'get_single_order': "https://api.bol.com/retailer/orders/",
#     'ship_order_item': "https://api.bol.com/retailer/orders/",
#     'ship_order_item_with_tracking_info': "https://api.bol.com/retailer/orders/",
#     'process_status': "https://api.bol.com/retailer/process-status/",
#     'get_offer_file': "https://api.bol.com/retailer/offers/export/",
#     'get_inventory': "https://api.bol.com/retailer/inventory?state=saleable&page=",
#     'export_single_offer': "https://api.bol.com/retailer/offers/",
#     'get_single_offer': "https://api.bol.com/retailer/offers/",
#     'delete_single_offer': "https://api.bol.com/retailer/offers/",
#     "get_unhandled_returns": "https://api.bol.com/retailer/returns?",
#     "get_handled_returns": "https://api.bol.com/retailer/returns/",
#     "get_all_returns_orders": "https://api.bol.com/retailer/returns?",
#     "create_new_offer": "https://api.bol.com/retailer/offers",
#     "update_offer": "https://api.bol.com/retailer/offers",
#     "update_product_stock": "https://api.bol.com/retailer/offers/",
#     "update_product_price": "https://api.bol.com/retailer/offers/",
#     "get_transporter": "https://api.bol.com/retailer/inbounds/fbb-transporters",
#     "update_transport_info": "https://api.bol.com/retailer/transports/",
#     "get_shipment_list": "https://api.bol.com/retailer/shipments?fulfilment-method=",
#     "get_single_shipment_list": "https://api.bol.com/retailer/shipments/",
#     "get_single_order_shipment_list": "https://api.bol.com/retailer/shipments?",
#     "retrive_shipment_status": "https://api.bol.com/retailer/process-status?",
#     "get_delivery_windows": "https://api.bol.com/retailer/inbounds/delivery-windows?",
#     "create_shipment": "https://api.bol.com/retailer/inbounds",
#     "get_product_label": "https://api.bol.com/retailer/inbounds/productlabels",
#     "get_shipping_label": "https://api.bol.com/retailer/inbounds/",
#     "get_packing_list": "https://api.bol.com/retailer/inbounds/",
#     "get_inbound_shipment": "https://api.bol.com/retailer/inbounds/",
#     "get_inbound_shipment_list": "https://api.bol.com/retailer/inbounds?page=",

#     "update_offer": "https://api.bol.com/retailer/offers/",
#     "update_product_stock": "https://api.bol.com/retailer/offers/",
#     "update_product_price": "https://api.bol.com/retailer/offers/",
#     "export_single_offer": "https://api.bol.com/retailer/offers/",
#     "delete_single_offer": "https://api.bol.com/retailer/offers/",
# }
