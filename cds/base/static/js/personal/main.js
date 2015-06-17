define(function (require, exports, module) {

  'use strict';

  /**
   * Module dependencies
   */

  var Grid = require('js/personal/component/grid');
  var Boxes = require('js/personal/component/boxes');
  var Box = require('js/personal/ui/box');

  /**
   * Module exports
   */

  return initialize;

  /**
   * Module function
   */

  function initialize() {
    var collection = 'home';
    Grid.attachTo('#grid', {
      collection: collection
    });
    Boxes.attachTo(document, {
      collection: collection,
      api: {
        boxes: '/api/personal_collection/'+collection,
        settings: '/api/personal_collection/settings',
      }
    });
    Box.attachTo('.personal-boxes', {
      collection: collection,
    });
  }
});
