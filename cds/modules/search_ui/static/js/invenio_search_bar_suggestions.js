function invenioSearchBarSuggestions() {
  function invenioSearchBarSuggestionsCtrl($scope, searchSuggestions) {
    $scope.updateHistory = function() {
      searchSuggestions.onSelect({label: $scope.dirty.value, value: $scope.dirty.value}, true);
    }

    $scope.autocomplete_options = {
      suggest: searchSuggestions.suggestStateRemote,
      on_select: searchSuggestions.onSelect,
      on_attach: function() { $scope.focused = true; },
    };
  }

  function link(scope, element, attrs, invenioSearchCtrl) {
    scope.dirty = {};
    scope.$watch(function () {
      return invenioSearchCtrl.userQuery;
    }, function (newValue, oldValue) {
      if (newValue && newValue !== oldValue) {
        scope.dirty.value = newValue;
      }
    });
  }

  return {
    restrict: 'AE',
    require: '^invenioSearch',
    link: link,
    controller: invenioSearchBarSuggestionsCtrl
  };
}

var invenioSearchDirectivesModule = angular.module('invenioSearch.directives');
// inject the dependencies by pushing them to 'require' as explained here: https://stackoverflow.com/a/32656843/6055311
invenioSearchDirectivesModule.requires.push(
  'MassAutoComplete', 'cdsSharedServices'
);
invenioSearchDirectivesModule.directive('invenioSearchBarSuggestions', invenioSearchBarSuggestions);
