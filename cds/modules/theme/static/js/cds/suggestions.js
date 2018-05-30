function searchSuggestions($sce, $q, $http, localStorageService) {
  function suggestStateRemote(term) {
    var deferred = $q.defer();

    $http({
      method: 'GET',
      url: '/api/records/',
      params: {
        q: term,
      },
    }).then(function (response) {
      var results = [];

      if (response.data.hits.hits) {
        angular.forEach(response.data.hits.hits, function (value, index) {
          results.push({
            label: value.metadata.title.title,
            value: value.metadata.title.title,
          });
        });
      }

      results = results.concat(localStorageService.get('cds.search.history') || []);
      deferred.resolve(results);
    });

    return deferred.promise;
  }

  function onSelect(selected, preventFormSubmit) {
    if (selected && !_.isEmpty(selected.value)) {
      try {
        var searches = localStorageService.get('cds.search.history') || [];
        var exists = _.find(searches, { value: selected.value });

        if (exists === undefined) {
          if (searches.length > 4) {
            searches.pop();
          }

          selected.label = '<i class="fa fa-history text-primary pr-5"></i> ' + selected.label;
          searches.push(selected);
          localStorageService.set('cds.search.history', searches);
        }

        // submit form to trigger search
        if (!preventFormSubmit) {
          /**
           * it is needed because when you selected an option by clicking not
           * hiting enter angular was throwing na `Error: [$rootScope:inprog]
           * $apply already in progress` trying to use $apply when angular is
           * running a $digest cycle. The error probably is comming from
           * massautocomplete.js that we use for autocompletion
           */
          setTimeout(function() {
            $('#cdsSearchFormSuggest').submit();
          });
        }
      } catch (error) {
      }
    }
  }

  return {
    onSelect: onSelect,
    suggestStateRemote: suggestStateRemote,
  };
}

angular.module('cdsSharedServices', ['ngSanitize', 'LocalStorageModule'])
  .factory('searchSuggestions', searchSuggestions);
