/*
 * This file is part of Invenio.
 * Copyright (C) 2015, 2016, 2017, 2018 CERN.
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

* In applying this license, CERN does not
* waive the privileges and immunities granted to it by virtue of its status
* as an Intergovernmental Organization or submit itself to any jurisdiction.
*/

// Bootstrap modules
angular.element(document).ready(function () {
  angular.bootstrap(
    document.getElementById('invenio-search'), ['cds', 'angular-loading-bar', 'ngDialog', 'invenioSearch']
  );
  angular.bootstrap(
    document.getElementById('cds-featured-video'), ['cds', 'invenioSearch']
  );
  angular.bootstrap(
    document.getElementById('cds-recent-videos'), ['cds', 'invenioSearch']
  );
});

function mainCtrl($scope, $sce, $q, $http, localStorageService, searchSuggestions) {
  $scope.dirty = {};

  $scope.updateHistory = function () {
    searchSuggestions.onSelect({ label: $scope.dirty.value, value: $scope.dirty.value }, true);
  }

  $scope.autocomplete_options = {
    suggest: searchSuggestions.suggestStateRemote,
    on_select: searchSuggestions.onSelect,
    on_attach: function () { $scope.focused = true; },
  };

  // Dismiss the popover by clicking outside
  $(document).on('click', function(e) {
    $('a[rel=popover]').each(function() {
      var $this = $(this);

      if (!$this.is(e.target) && $this.has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
        $this.popover('hide').data('bs.popover').inState.click = false;
      }
    });
  });
};

angular.module('cdsSuggest', ['MassAutoComplete', 'cdsSharedServices'])
  .controller('mainCtrl', mainCtrl);

/**
 * Additional fun features
 */
$(document).ready(function () {
  function rainbowShow() {
    var _c = '.unicorn-rainbow';
    if ($(_c).length == 0) {
      $('body').append(
        $('<img>', {
          class: 'unicorn-rainbow',
          src: '/static/img/unicorn.png'
        })
      );
    }
    $(_c).css({ left: 0 }).show();
    $(_c).animate({
      left: $(window).width(),
    }, 1000, function () {
      $(_c).hide();
    });
  }

  function toggleAnnouncement() {
    $.get('/api/announcement', { pathname: location.pathname }, function (result) {
      if (result && result.message) {
        $('#announcement')
          .addClass('alert-' + result.style)
          .removeClass('hidden')
          .html(result.message);

        // Hack to fix wrong margin on deposit view
        $('#cds-deposit').addClass('fix-margin-top');
      } else {
        $('#announcement').addClass('hidden');
      }
    });
  }

  // Load and show any announcement message
  toggleAnnouncement();

  $('#cds-navbar-form-input').focus(function () {
    $('.cds-navbar-form').addClass('cds-active-search');
  }).blur(function () {
    $('.cds-navbar-form').removeClass('cds-active-search');
  });

  // Focus when pressing ``l``
  Mousetrap.bind('l', function () {
    $('#cds-navbar-form-input').focus();
    setTimeout(function () {
      $('#cds-navbar-form-input').val('');
    }, 0);
  });

  Mousetrap.bind('c d s g r e a t', function () {
    rainbowShow();
  });
});
