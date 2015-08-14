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

'use strict';


define([
  'js/record_tools',
  'jasmine-jquery',
], function(jasmineJQuery) {
  "use strict"

  describe("See more modal pagination suite", function() {
    var data_item_number = 12;
    var page_size = 5;

    beforeEach(function () {
      $("#test-see-more-modal").remove();
      jasmine.getFixtures().fixturesPath = '/jasmine/spec/cds.base/fixtures/';

      var data_items = new Array(data_item_number);

      data_items = $.map(data_items, function(e) { return 'item' });
      var data_json = JSON.stringify(data_items);

      $('body').append(readFixtures('see_more_modal.html'));
      $("#test-see-more-modal")
        .attr("data-items", data_json)
        .attr("data-page-size", page_size);

    });

    afterEach(function(){
      $('#test-see-more-modal').remove();
      $('.cds-modal').remove();
    });

    it("data-show-more link click creates a new modal with expand button", function() {
      expect('.cds-modal').not.toExist();

      $("a[data-show-more]").trigger('click');

      expect('.cds-modal').toExist();
      expect("#cds-modal-expand-btn").toExist();
    });

    it("modal has a proper number of items", function() {
      $("a[data-show-more]").trigger('click');

      var cds_modal_list = $("#pages");
      expect(cds_modal_list.children().length).toEqual(data_item_number);
    });

    it("modal displays only a defined page size elements", function() {
      $("a[data-show-more]").trigger('click');

      var cds_visible_list = $("#pages").find("li:visible");
      expect(cds_visible_list.length).toEqual(page_size);
    });

    it("load more button exists", function() {
      $("a[data-show-more]").trigger('click');
      expect("#cds-modal-expand-btn").toExist();
    });

    it("load more button expands number of visible items by page_size", function() {
      $("a[data-show-more]").trigger('click');
      $("#cds-modal-expand-btn").trigger('click');

      var cds_visible_list = $("#pages").find("li:visible");
      expect(cds_visible_list.length).toEqual(2*page_size);
    });

    it("load more button checks if the items limit was reached", function() {
      $("a[data-show-more]").trigger('click');
      $("#cds-modal-expand-btn")
        .trigger('click')
        .trigger('click');

      var cds_visible_list = $("#pages").find("li:visible");
      expect(cds_visible_list.length).toEqual(data_item_number);
    });
  });
});
