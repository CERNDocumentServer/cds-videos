/*
 * This file is part of Invenio.
 * Copyright (C) 2015, 2016, 2017 CERN.
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
      var results = localStorageService.get('cds.search.history') || [];
      if (response.data.hits.hits) {
        angular.forEach(response.data.hits.hits, function(value, index) {
          results.push({
            label: value.metadata.title.title,
            value: value.metadata.title.title
          })
        });
      }
      results.reverse();
      deferred.resolve(results);
    });
    return deferred.promise;
  }
  function onSelect(selected) {
    if (selected && !_.isEmpty(selected.value)){
      try {
        var searches = localStorageService.get('cds.search.history') || [];
        var exists = _.findWhere(searches, {value: selected.value});
        if (exists === undefined) {
          if (searches.length > 4){
            searches.pop();
          }
          selected.label = '<i class="fa fa-history text-primary pr-5"></i> ' + selected.label;
          searches.push(selected);
          localStorageService.set('cds.search.history', searches);
        }
      } catch(error) {
        // Error no worries..
      }
    }
  }
  $scope.updateHistory = function() {
    onSelect({label: $scope.dirty.value, value: $scope.dirty.value});
  }
  $scope.autocomplete_options = {
    suggest: suggest_state_remote,
    on_attach: onAttach,
    on_select: onSelect,
  };
});


$(document).ready(function() {
  $('#cds-navbar-form-input').focus(function() {
    $(".cds-navbar-form").addClass('cds-active-search');
  })
  .blur(function() {
    $(".cds-navbar-form").removeClass('cds-active-search');
  });
});
