odoo.define('bol_ept.graph', function (require) {
    "use strict";

    var fieldRegistry = require('web.field_registry');
    var AbstractField = require('web.AbstractField');
    var graph_ept = require('graph_widget_ept.graph');
    var core = require('web.core');
    var QWeb = core.qweb;

    graph_ept.EmiproDashboardGraph.include({
        events: _.extend({}, graph_ept.EmiproDashboardGraph.prototype.events || {}, {
            'change #sort_order_data_bol': '_sortBolOrders',
            'click #instance_fbr_order': '_getFbrOrders',
            'click #instance_fbb_order': '_getFbbOrders',
        }),

        _sortBolOrders: function(e) {
          var self = this;
          this.context.fulfillment_by = e.currentTarget.value
            return this._rpc({model: self.model,method: 'read',args:[this.res_id],'context':this.context}).then(function (result) {
                if(result.length) {
                    self.graph_data = JSON.parse(result[0][self.match_key])
                    self.on_attach_callback()
                }
            })
        },

         /*Render action for  Sales Order */
                        _getFbrOrders: function () {
                            return this.do_action(this.graph_data.fbr_order_data.order_action)
                        },

        /*Render action for  Sales Order */
                        _getFbbOrders: function () {
                            return this.do_action(this.graph_data.fbb_order_data.order_action)
                        },


    });

});