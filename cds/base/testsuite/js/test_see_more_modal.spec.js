/*
 * This file is part of Invenio.
 * Copyright (C) 2014, 2015 CERN.
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

  describe("See more modal suite", function() {
    var data_item_number = 10;
    var page_size = 15;

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

    it("modal has a proper number of items", function() {
      $("a[data-show-more]").trigger('click');

      var cds_modal_list = $("#pages");
      expect(cds_modal_list.children().length).toEqual(data_item_number);
    });

    it("data-show-more link click creates a new modal without expand button", function() {
      expect('.cds-modal').not.toExist();

      $("a[data-show-more]").trigger('click');

      expect('.cds-modal').toExist();
      expect("#cds-modal-expand-btn").not.toExist();
    });

    it("modal has a proper number of items", function() {
      $("a[data-show-more]").trigger('click');

      var cds_modal_list = $("#pages");
      expect(cds_modal_list.children().length).toEqual(data_item_number);
    });

    it("modal displays all of the items", function() {
      $("a[data-show-more]").trigger('click');

      var cds_visible_list = $("#pages").find("li:visible");
      expect(cds_visible_list.length).toEqual(data_item_number);
    });
  });
});
