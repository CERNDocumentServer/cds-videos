/*
 * This file is part of Invenio.
 * Copyright (C) 2015 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

define(function (require) {

  var _ = require('vendors/lodash/lodash');
  var defineComponent = require('flight/lib/component');
  var errorMessage = require('hgn!./../templates/error');
  var sortable = require('vendors/sortable.js/Sortable');

  function Grid() {
    this.defaultAttrs({
      isGuest: null,
      collection: null,
      ID: 'personal-grid-handler',
      maxBoxesOnGrid: 9,
      addBoxSelector: '.personal-boxes-add-more',
      dragHandle: '.personal-box',
      errorMessage: '.personal-grid-error-message',
      gridLoader: '.personal-grid-loader',
      namespace: null,
    });

    // Init
    this.init = function (ev, args) {
      var that = this;
      if (!that.attr.isGuest) {
        var el = document.getElementById(that.attr.ID);
        localStorage.setItem(that.attr.namespace, localStorage.getItem('boxes'));
        // delete localStorage
        sortable.create(el, {
          animation: 250,
          dataIdAttr: 'data-id',
          handle: that.attr.dragHandle,
          group: that.attr.namespace,
          onUpdate: function(evt) {
            setTimeout(function() {
              that.trigger(document, 'personal.boxes.data.order');
            }, 0);
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
      }
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
