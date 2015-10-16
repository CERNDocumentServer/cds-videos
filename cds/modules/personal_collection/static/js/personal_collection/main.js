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

  'use strict';

  /**
   * Module dependencies
   */

  var Grid = require('js/personal_collection/component/grid');
  var Boxes = require('js/personal_collection/component/boxes');
  var Box = require('js/personal_collection/ui/box');

  /**
   * Module exports
   */

  return initialize;

  /**
   * Module function
   */

  function initialize() {
    var collection = 'home';
    var container = '#grid';
    var $grid = $(container);
    var isGuest = $grid.data('guest');

    Grid.attachTo(container, {
      isGuest: isGuest,
      collection: collection,
      namespace: 'grid-' + collection
    });

    Boxes.attachTo(document, {
      api: {
        boxes: '/api/personal_collection/'+collection,
        settings: '/api/personal_collection/settings',
      },
      collection: collection,
      isGuest: isGuest,
      namespace: 'grid-' + collection
    });

    Box.attachTo('.personal-boxes', {
      collection: collection,
      isGuest: isGuest,
      namespace: 'grid-' + collection
    });
  }
});
