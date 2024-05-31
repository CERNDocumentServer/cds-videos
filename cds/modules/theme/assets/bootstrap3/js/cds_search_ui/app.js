import angular from "angular";
import $ from "jquery";
import * as d3 from "d3";
import "angular-loading-bar";
import "angular-mass-autocomplete";
import "ng-dialog";

import "invenio-search-js/dist/invenio-search-js";
import "@js/cds/suggestions";
import "@js/cds_deposit/app";
//import "@js/cds/app";

function invenioSearchBarSuggestions() {
  function invenioSearchBarSuggestionsCtrl($scope, searchSuggestions) {
    $scope.updateHistory = function () {
      searchSuggestions.onSelect(
        { label: $scope.dirty.value, value: $scope.dirty.value },
        true
      );
    };

    $scope.autocomplete_options = {
      suggest: searchSuggestions.suggestStateRemote,
      on_select: searchSuggestions.onSelect,
      on_attach: function () {
        $scope.focused = true;
      },
    };
  }

  function link(scope, element, attrs, invenioSearchCtrl) {
    scope.dirty = {};
    scope.$watch(
      function () {
        return invenioSearchCtrl.userQuery;
      },
      function (newValue, oldValue) {
        if (newValue && newValue !== oldValue) {
          scope.dirty.value = newValue;
        }
      }
    );
  }

  return {
    restrict: "AE",
    require: "^invenioSearch",
    link: link,
    controller: invenioSearchBarSuggestionsCtrl,
  };
}

var invenioSearchDirectivesModule = angular.module("invenioSearch.directives");
// inject the dependencies by pushing them to 'require' as explained here: https://stackoverflow.com/a/32656843/6055311
invenioSearchDirectivesModule.requires.push(
  "MassAutoComplete",
  "cdsSharedServices"
);
invenioSearchDirectivesModule.directive(
  "invenioSearchBarSuggestions",
  invenioSearchBarSuggestions
);

angular.element(document).ready(function () {
  angular.bootstrap(document.getElementById("cds-deposit-index"), [
    "cds",
    "angular-loading-bar",
    "ngDialog",
    "invenioSearch",
    "cdsDeposit",
  ]);
});

$(document).ready(function () {
  $(".dropdown-toggle").dropdown();
});
