function cdsAPI($q, $http) {

  function action(url, method, payload, mimetype) {
    requestConfig = {
      url: url,
      method: method,
      data: payload
    };

    if (mimetype) {
      requestConfig.headers = {
        'Content-Type': mimetype
      }
    }

    return $http(requestConfig);
  }

  function chainedActions(promises) {
      var defer = $q.defer();
      var data = [];
      function _chain(promise) {
        var fn = promise;
        var callback;

        if (typeof(promise) !== 'function') {
          fn = promise[0];
          callback = promise[1];
        }
        fn().then(
          function(_data) {
            data.push(_data);
            if (typeof(callback) === 'function') {
              // Call the callback
              callback(_data);
            }
            if (promises.length > 0) {
              return _chain(promises.shift());
            } else {
              defer.resolve(data);
            }
          }, function(error) {
            defer.reject(error);
          }
        );
      }
      _chain(promises.shift());
      return defer.promise;
  }

  function cleanData(data, unwanted) {
    var _unwantend = unwanted || [[null], [undefined]];
    // Delete the _files before request
    delete data._files;
    angular.forEach(data, function(value, key) {
      angular.forEach(_unwantend, function(_value) {
        if (angular.equals(_value, value))  {
          delete data[key];
        }
      });
    });
    return data;
  }

  function getUrlPath(url) {
    var _parser = document.createElement('a');
    _parser.href = url;
    return _parser.pathname;
  }

  function resolveJSON(url) {
    return $http.get(url);
  }

  return {
    action: action,
    cleanData: cleanData,
    chainedActions: chainedActions,
    resolveJSON: resolveJSON,
    getUrlPath: getUrlPath,
  };
}

cdsAPI.$inject = [
  '$q',
  '$http',
];

angular.module('cdsDeposit.factories')
  .factory('cdsAPI', cdsAPI);
