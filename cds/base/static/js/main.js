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

require([
    "jquery",
    "js/app",
    "js/record_tools",
  ],
  function($, app, record_tools) {

    $(document).ready(function() {
      record_tools.modalList();
      record_tools.expandContent();
      record_tools.translationListener();

      // Search bar remove collection tag
      var $searchForm = $('#cds-main-search');
      var $searchInput = $('#cds-main-search-input');
      $('.cds-remove-search-to-collection').on('click', function(ev) {
        ev.preventDefault();
        $searchForm.find('[name=cc]').val('');
        $(this).parent().fadeOut('slow').remove();
      });
    });
});
