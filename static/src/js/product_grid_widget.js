odoo.define('plannificateur_reapprovisionnemnt.ProductGridWidget', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var QWeb = core.qweb;

    var ProductGridWidget = AbstractField.extend({
        template: 'ProductGridWidget',
        events: {
            'click .month-header': '_onToggleGroup',
            'change .forecast-input': '_onChangeForecast'
        },

        init: function () {
            this._super.apply(this, arguments);
            this.groupedData = {};
        },

        _render: function () {
            var self = this;
            if (!this.value) {
                return;
            }

            // Grouper les données par mois
            this.groupedData = _.groupBy(this.value, 'month_name');

            // Préparer les données pour le template
            var months = _.map(this.groupedData, function (products, month) {
                return {
                    month: month,
                    products: products,
                    isOpen: true // Par défaut ouvert
                };
            });

            // Trier les mois chronologiquement
            months = _.sortBy(months, function (m) {
                var date = moment(m.products[0].month_date);
                return date.format('YYYY-MM');
            });

            this.$el.html(QWeb.render('ProductGridContent', {
                months: months,
                widget: this
            }));

            // Appliquer les styles
            this.$el.find('.month-group').addClass('table table-bordered');
            this.$el.find('.month-header').addClass('bg-light font-weight-bold p-2');
        },

        _onToggleGroup: function (ev) {
            var $header = $(ev.currentTarget);
            var $content = $header.next('.month-content');
            $content.toggleClass('d-none');
            $header.find('.toggle-icon').toggleClass('fa-caret-right fa-caret-down');
        },

        _onChangeForecast: function (ev) {
            var $input = $(ev.currentTarget);
            var productId = $input.data('product-id');
            var monthDate = $input.data('month-date');
            var value = parseFloat($input.val());

            // Mettre à jour la valeur dans le modèle
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: {
                    forecast_qty: value,
                    product_id: productId,
                    month_date: monthDate
                },
            });
        },
    });

    field_registry.add('product_grid', ProductGridWidget);

    return ProductGridWidget;
}); 