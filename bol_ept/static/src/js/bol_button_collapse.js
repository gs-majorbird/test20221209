odoo.define('bol_ept.bol_collapse_button', function (require) {
"use strict";
    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var UploadBillMixin = require('account.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');
    var _t = core._t;

    var collapseButtonKanbanController = KanbanController.extend(UploadBillMixin, {
        events: _.extend({}, KanbanController.prototype.events, {
            'click #bol_button_toggle': '_toggleBtn',
        }),
        /**
         * To toggle the OnBoarding button to hide /show the panel
         */
        _toggleBtn: _.debounce(function (ev) {
            var self = this
            return this._rpc({
                model: 'res.company',
                method: 'action_toggle_bol_instances_onboarding_panel',
                args: [parseInt(ev.currentTarget.getAttribute('data-company-id'))],
            }).then(function(result) {
                if(result == 'closed'){
                    $('.o_onboarding_container.collapse').collapse('hide')
                    $('#bol_button_toggle').html('Create more Bol instance').css({"background-color":"#ececec","border":"1px solid #ccc"});
                } else {
                    $('.o_onboarding_container.collapse').collapse('show')
                    $('#bol_button_toggle').html('Hide On boarding Panel').css({"background-color":"","border": ""});
                }
            }).guardedCatch(function (error) {
                self.do_warn(_t('Warning'), _t('Something Went Wrong'));
            });
        }, 300),
    });

    var BolOnBoardingToggleKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: collapseButtonKanbanController,
        }),
    });

    viewRegistry.add('BolOnBoardingToggle', BolOnBoardingToggleKanbanView);
});
