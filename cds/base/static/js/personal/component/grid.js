define(function (require) {

  var _ = require('vendors/lodash/lodash');
  var defineComponent = require('flight/lib/component');
  var errorMessage = require('hgn!./../templates/error');
  var sortable = require('vendors/sortable.js/Sortable');

  function Grid() {
    this.defaultAttrs({
      ID: 'personal-grid-handler',
      collection: null,
      maxBoxesOnGrid: 9,
      addBoxSelector: '.personal-boxes-add-more',
      dragHandle: '.personal-box',
      errorMessage: '.personal-grid-error-message',
      gridLoader: '.personal-grid-loader',
    });

    // Init
    this.init = function (ev, args) {
      var that = this;
      var el = document.getElementById(that.attr.ID);
      localStorage.setItem('grid-'+this.attr.collection, localStorage.getItem('boxes'));
      // delete localStorage
      sortable.create(el, {
        animation: 250,
        dataIdAttr: 'data-id',
        handle: that.attr.dragHandle,
        group: 'grid-' + this.attr.collection,
        onUpdate: function(evt) {
          that.trigger(document, 'personal.boxes.data.order');
        },
        store: {
          get: function(sortable) {
            var order = localStorage.getItem(sortable.options.group.name);
            return order ? order.split(',') : [];
          },
          set: function(sortable) {
            var order = sortable.toArray();
            localStorage.setItem(sortable.options.group.name, order.join(','));
          }
        }
      });
    };

    this.checkLimits = function(ev, args) {
      var boxes = localStorage.getItem('boxes') || "";
      var overLimit = _.size(boxes.split(',')) >= this.attr.maxBoxesOnGrid;
      if (overLimit) {
        this.trigger(document, 'personal.wrapper.button.hide');
      } else {
        this.trigger(document, 'personal.wrapper.button.show');
      }
    };

    this.showAddButton = function(ev, args) {
      $(this.attr.addBoxSelector).show();
    };

    this.hideAddButton = function(ev, args){
      $(this.attr.addBoxSelector).hide();
    };

    this.showLoader = function(ev, args){
      $(this.attr.gridLoader).css('visibility', 'visible');
    };

    this.hideLoader = function(ev, args){
      $(this.attr.gridLoader).css('visibility', 'hidden');
    };

    this.errorMessage = function(ev, args) {
      $(this.attr.errorMessage).html(errorMessage(args));
    };

    // After initialization
    this.after('initialize', function () {
      this.on(document, 'personal.boxes.ui.initizalized', this.init);
      this.on(document, 'personal.wrapper.loader.hide', this.hideLoader);
      this.on(document, 'personal.wrapper.loader.show', this.showLoader);
      this.on(document, 'personal.boxes.error', this.errorMessage);
      this.on(document, 'personal.wrapper.check.button.limits', this.checkLimits);
      this.on(document, 'personal.wrapper.button.hide', this.hideAddButton);
      this.on(document, 'personal.wrapper.button.show', this.showAddButton);
      this.on(document, 'personal.boxes.error', this.errorMessage);

      this.trigger(document, 'personal.wrapper.check.button.limits');
    });
  }

  return defineComponent(Grid);
});
