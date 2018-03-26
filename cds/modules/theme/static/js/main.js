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
angular.element(document).ready(function() {
  angular.bootstrap(
    document.getElementById("invenio-search"), ['cds', 'angular-loading-bar', 'ngDialog', 'invenioSearch']
  );
  angular.bootstrap(
    document.getElementById("cds-featured-video"), [ 'cds', 'invenioSearch']
  );
  angular.bootstrap(
    document.getElementById("cds-recent-videos"), [ 'cds', 'invenioSearch']
  );
});

var app = angular.module('cdsSuggest', ['ngSanitize', 'MassAutoComplete', 'LocalStorageModule']);
app.controller('mainCtrl', function ($scope, $sce, $q, $http, localStorageService) {
  $scope.dirty = {};
  var url = '/api/records/';
  function onAttach() {
    $scope.focused = true;
  }
  function suggest_state_remote(term) {
    var deferred = $q.defer();
    $http({
      method: 'GET',
      url: url,
      params: {
        q: term
      }
    }).then(function(response) {
      var results = [];
      if (response.data.hits.hits) {
        angular.forEach(response.data.hits.hits, function(value, index) {
          results.push({
            label: value.metadata.title.title,
            value: value.metadata.title.title
          })
        });
      }
      results = results.concat(localStorageService.get('cds.search.history') || []);
      deferred.resolve(results);
    });
    return deferred.promise;
  }
  function onSelect(selected, preventFormSubmit) {
    if (selected && !_.isEmpty(selected.value)){
      try {
        var searches = localStorageService.get('cds.search.history') || [];
        var exists = _.find(searches, {value: selected.value});
        if (exists === undefined) {
          if (searches.length > 4){
            searches.pop();
          }
          selected.label = '<i class="fa fa-history text-primary pr-5"></i> ' + selected.label;
          searches.push(selected);
          localStorageService.set('cds.search.history', searches);
        }
        // submit form to trigger search
        if (!preventFormSubmit) {
          // it is needed because when you selected an option by clicking not
          // hiting enter angular was throwing na `Error: [$rootScope:inprog]
          // $apply already in progress` trying to use $apply when angular is
          // running a $digest cycle. The error probably is comming from
          // massautocomplete.js that we use for autocompletion
          setTimeout(function() {
            $("[name='cdsSearchFormSuggest']").submit();
          });
        }
      } catch(error) {
        // Error no worries..
      }
    }
  }
  $scope.updateHistory = function() {
    onSelect({label: $scope.dirty.value, value: $scope.dirty.value}, true);
  }
  $scope.autocomplete_options = {
    suggest: suggest_state_remote,
    on_attach: onAttach,
    on_select: onSelect,
  };
});

// Make sure navigation is on focus
$(document).ready(function() {
  // load and show any announcement message
  toggleAnnouncement();

  $('#cds-navbar-form-input').focus(function() {
    $(".cds-navbar-form").addClass('cds-active-search');
  })
  .blur(function() {
    $(".cds-navbar-form").removeClass('cds-active-search');
  });

  // Focus when pressing ``l``
  Mousetrap.bind('l', function() {
    $('#cds-navbar-form-input').focus();
    setTimeout(function() {
      $('#cds-navbar-form-input').val('');
    },0);
  });

  Mousetrap.bind('c d s g r e a t', function() {
    // Start rainbow show
    rainbowShow();
  });
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
    $(_c).css({left:0}).show();
    $(_c).animate({
      left: $(window).width(),
    }, 1000, function() {
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

        // hack to fix wrong margin on deposit view
        $('#cds-deposit').addClass('fix-margin-top');
      } else {
        $('#announcement').addClass('hidden');
      }
    });
  }
});
