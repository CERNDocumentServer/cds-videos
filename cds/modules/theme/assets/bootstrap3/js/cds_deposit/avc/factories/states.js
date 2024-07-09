import angular from "angular";

import { getCookie } from "../../../getCookie";

import "../providers/depositActions";
function cdsAPI($q, $http, depositActions, urlBuilder) {
  function action(url, method, payload, headers) {
    var requestConfig = {
      url: url,
      method: method,
      data: payload,
    };

    if (headers) {
      requestConfig.headers = headers;
    }

    if (["POST", "PUT", "PATCH", "DELETE"].indexOf(method) > -1) {
      requestConfig.headers = {
        ...requestConfig.headers,
        "X-CSRFToken": getCookie("csrftoken"),
      };
    }

    return $http(requestConfig);
  }

  function chainedActions(promises) {
    var defer = $q.defer();
    var data = [];
    function _chain(promise) {
      var fn = promise;
      var callback;

      if (typeof promise !== "function") {
        fn = promise[0];
        callback = promise[1];
      }
      fn().then(
        function (_data) {
          data.push(_data);
          if (typeof callback === "function") {
            // Call the callback
            callback(_data);
          }
          if (promises.length > 0) {
            return _chain(promises.shift());
          } else {
            defer.resolve(data);
          }
        },
        function (error) {
          defer.reject(error);
        }
      );
    }
    _chain(promises.shift());
    return defer.promise;
  }

  function cleanData(data, unwanted) {
    var _unwantend = unwanted || [[null], [undefined]];
    data = angular.copy(data);
    // Delete the _files before request
    delete data._files;
    angular.forEach(data, function (value, key) {
      angular.forEach(_unwantend, function (_value) {
        if (angular.equals(_value, value)) {
          delete data[key];
        }
      });
    });
    return data;
  }

  function getUrlPath(url) {
    var _parser = document.createElement("a");
    _parser.href = url;
    return _parser.pathname;
  }

  function resolveJSON(url) {
    return $http({
      url: url,
      method: "GET",
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: 0,
      },
    });
  }

  function containsLink(links, link) {
    return links && Object.keys(links).indexOf(link) > -1;
  }

  function guessEndpoint(record, depositType, actionName, links) {
    var link = depositActions[depositType][actionName].link,
      isMaster = depositType === "project";

    if (containsLink(links, link)) {
      return links[link];
    } else {
      if (!isMaster) {
        // If the link is self just return the self video url
        if (link === "self") {
          return urlBuilder.selfVideo({
            deposit: record._deposit.id,
          });
        } else if (link === "bucket") {
          return urlBuilder.bucketVideo({
            bucket: record._buckets.deposit,
          });
        }
        // If the link is different return the action video url
        return urlBuilder.actionVideo({
          deposit: record._deposit.id,
          action: actionName.toLowerCase(),
        });
      }
    }
  }

  function makeAction(url, depositType, actionName, payload) {
    var actionInfo = depositActions[depositType][actionName];
    if (actionInfo.preprocess) {
      payload = actionInfo.preprocess(payload);
    }
    return action(url, actionInfo.method, payload, actionInfo.headers);
  }

  return {
    action: action,
    cleanData: cleanData,
    chainedActions: chainedActions,
    resolveJSON: resolveJSON,
    getUrlPath: getUrlPath,
    guessEndpoint: guessEndpoint,
    makeAction: makeAction,
  };
}

cdsAPI.$inject = ["$q", "$http", "depositActions", "urlBuilder"];

angular.module("cdsDeposit.factories").factory("cdsAPI", cdsAPI);
