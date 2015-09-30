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

  var $ = require('jquery');
  // Components
  var _ = require('vendors/lodash/lodash');
  var async = require('vendors/async/lib/async');
  var boxStorage = require('js/personal/helpers/boxStorage');
  var defineComponent = require('flight/lib/component');

  // Templates
  var wrapperTemplate = require('hgn!./../templates/layout');
  var navTemplate = require('hgn!./../templates/nav');
  var headerTemplate = require('hgn!./../templates/header');
  var footerTemplate = require('hgn!./../templates/footer');
  var selectBox = require('hgn!./../templates/new');

  function Box() {
    this.defaultAttrs({
      isGuest: null,
      namespace: null,
      storage: boxStorage,
      // Box Specific elements
      boxBodySelector: '.personal-box-body',
      boxLoadingSelector: '.personal-box-loading',
      // Action links
      addBox: '.personal-boxes-add-more',
      deleteBox: '.personal-box-ui-delete',
      editBox: '.personal-box-ui-edit',
      normalBox: '.personal-box-ui-normal',
      saveBox: '.personal-box-ui-save',
      selectBox: '.personal-box-ui-select',
      stateBox: '.personal-box-ui-state',
      // Templates
      templates: {
        default: {
          normal: require('hgn!./../templates/normal/default'),
          edit: require('hgn!./../templates/edit/default')
        },
        record_list: {
          normal: require('hgn!./../templates/normal/record_list'),
          edit: require('hgn!./../templates/edit/record_list')
        },
        issue: {
          normal: require('hgn!./../templates/normal/issue'),
          edit: require('hgn!./../templates/edit/issue')
        }
      }
    });

    this.init = function(ev, data) {
      // Empty the space
      var that = this;
      var boxes = that.attr.storage.all();
      that.$node.empty();
      async.forEach(
        boxes,
        function(box, callback) {
          // add the box Skeleton
          that._addBoxSkeleton(box);
          // callback for the next one
          callback();
        },
        function(error) {
          if (error) {
            that._error(error);
          }
          // Trigger render boxes to normal mode
          that.trigger(document, 'personal.boxes.ui.normal', {
            ids: _.pluck(boxes, 'id')
          });
          that.trigger(document, 'personal.boxes.ui.initizalized');
        }
      );
    };

    this.normalBoxView = function(ev, args) {
      ev.preventDefault();
      this.processView(ev.target, args, 'normal');
    };

    this.selectBoxView = function(ev, args) {
      ev.preventDefault();
      this.processView(ev.target, args, 'select');
    };

    this.editBoxView = function(ev, args) {
      ev.preventDefault();
      this.processView(ev.target, args, 'edit');
    };

    this.newBoxAction = function(ev, args) {
      ev.preventDefault();
      var id = this._addBoxSkeleton();
      this.trigger(document, 'personal.boxes.ui.select', {
        ids: [id]
      });
      this.trigger(document, 'personal.wrapper.check.button.limits');
    };

    this.selectBoxAction = function(ev, args) {
      ev.preventDefault();
      var id = this._getIDFromTarget(ev.target);
      var data = this._getFormData(id);
      var box = this.attr.storage.get(id);
      box._settings.type = data.template;
      this.attr.storage.update(box);
      this.trigger(document, 'personal.boxes.ui.edit', {
        ids: [id]
      });
    };

    this.deleteBoxAction = function(ev, args) {
      ev.preventDefault();
      // Get box ID from event.target element
      var id = args.id || this._getIDFromTarget(ev.target);
      // Get box jQuery element by id
      var $box = this._getBoxElement(id);
      // get the box settings
      var box = this.attr.storage.get(id);
      var isNew = (_.isUndefined(box.dummy)) ? false : true;
      this.attr.storage.destroy(id);
      // Destroy it from DOM
      $box.remove();
      if (!isNew) {
        this.trigger(document, 'personal.boxes.data.delete', {
          id: id,
        });
      }
      this.trigger(document, 'personal.wrapper.check.button.limits');
    };

    this.saveBoxAction = function (ev, args) {
      ev.preventDefault();
      var id = args.id || this._getIDFromTarget(ev.target);
      var data = this._getFormData(id);
      this._boxLoadingShow(id);
      var $box = this._getBoxElement(id);
      this._changeState($box, 'loading');
      this.trigger(document, 'personal.boxes.data.update', {
        id: id,
        data: data
      });
    };

    this.render = function($el, template, data) {
      // Render the template
      var html = template(data);
      $el.html(html);
    };

    this.processView = function(target, args, state) {
      var that = this;
      var isElement = _.isElement(target);
      var ids = isElement ? [that._getIDFromTarget(target)] : args.ids;
      async.forEach(ids, function(id, callback) {
        that._processBox(id, state);
        callback();
      }, function(error) {
          if (error) {
            that._error(error);
          }
      });
    };

    this._processBox = function(id, state) {
      this._boxLoadingShow(id);
      var box = this.attr.storage.get(id);
      var $box = this._getBoxElement(id);
      var $content = $box.find(this.attr.boxBodySelector);
      var template = this._decideTemplate({
        type: box._settings.type,
        state: state
      });
      this.render($content, template, box);
      this._changeState($box, state);
      this._boxLoadingHide(id);
    };

    this._decideTemplate = function(args) {
      if (args.state === 'select') {
        return selectBox;
      }
      try {
        return this.attr.templates[args.type][args.state];
      } catch (error) {
        return this.attr.templates['default'][args.state];
      }
    };

    this._addBoxSkeleton = function(args) {
      var isNew = _.isUndefined(args);
      var box = !isNew ? args : this._getDefaultBox();
      var html = wrapperTemplate(box, {
        nav: navTemplate.template,
        header: headerTemplate.template,
        footer: footerTemplate.template,
      });
      if (isNew) {
        this.attr.storage.save(box)
      }
      this.$node.append(html);
      return box.id;
    };

    this._getDefaultBox = function() {
      var box = {
        id: this._tempIDGenerator(),
        dummy: true,
        _settings: {
          type: 'dummy'
        }
      };
      return box;
    };

    this._getBoxElement = function (id) {
      return $('[data-id='+id+']').first();
    };

    this._getIDFromTarget = function (target){
      var $target = $(target);
      var id = $target
        .closest('[data-id]')
        .first()
        .data('id');
      return id;
    };

    this._getFormData = function(id){
      // Get the content
      var $content = this._getBoxElement(id);
      var data = $content.find('form').serializeArray();
      return _.zipObject(_.map(data, _.values));
    };

    this._boxLoadingShow = function(id) {
      var $box = this._getBoxElement(id);
      $box.find(this.attr.boxLoadingSelector)
        .first()
        .show();
    };

    this._boxLoadingHide = function(id) {
      var $box = this._getBoxElement(id);
      $box.find(this.attr.boxLoadingSelector)
        .first()
        .hide();
    };

    this._changeState = function($el, state) {
      $el.find('[data-show]').each(function(index, item){
        var $item = $(item);
        if ($item.data('show') != state) {
          $item.hide();
        } else {
          $item.show();
        }
      });
    }

    this._tempIDGenerator = function(){
      var boxes = this.attr.storage.all();
      return _.size(boxes) + 1;
    }

    this._error = function(error) {
      this.trigger(document, 'personal.boxes.error', {
        message: (error.status == 401) ? 'You must be logged in' : 'Sorry an error occured'
      });
    };

    this.after('initialize', function() {
      this.on(document, 'personal.boxes.ui.normal', this.normalBoxView);
      this.on(document, 'personal.boxes.ui.edit', this.editBoxView);
      this.on(document, 'personal.boxes.ui.select', this.selectBoxView);
      this.on(document, 'click', {
        'addBox': this.newBoxAction,
        'deleteBox': this.deleteBoxAction,
        'selectBox': this.selectBoxAction,
        'saveBox': this.saveBoxAction,
        'normalBox': this.normalBoxView,
        'editBox': this.editBoxView,
      });
      // Initialize everything
      this.on(document, 'personal.boxes.data.initialized', this.init);
    });
  }
  // Define flightjs component
  return defineComponent(Box);
});
