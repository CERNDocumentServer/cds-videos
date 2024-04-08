import angular from "angular";

function cdsRemoteUploadCtrl($scope, $http, $element, $q) {
  var that = this;
  this.$onInit = function () {
    $scope.startUrlUploads = function (urls) {
      var _urls = urls.split("\n");
      var urlsResolved = $q.all(
        _urls.map(function (url) {
          // Use an a element to parse the URL
          var parser = document.createElement("a");
          parser.href = url;
          var name = decodeURIComponent(parser.pathname.split("/").pop());
          var obj = {
            key: name,
            name: name,
            receiver: that.cdsDepositsCtrl.isVideoFile(name)
              ? that.remoteMasterReceiver
              : that.remoteChildrenReceiver,
            url: url,
          };
          var sizePromise;
          // Retrieve the file size if the protocol is http/s
          if (url.startsWith("http")) {
            sizePromise = $http.head(url).then(function (response) {
              var len = response.headers("content-length");
              if (len) {
                obj.size = len;
              }
            });
          } else {
            sizePromise = $q.resolve();
          }
          // Return the object wrapped in a promise
          return sizePromise.catch(angular.noop).then(function () {
            return obj;
          });
        })
      );
      // When all the objects have been formed, add them as files
      urlsResolved.then(function (objs) {
        var ctrl = that.cdsUploaderCtrl || that.cdsDepositsCtrl;
        ctrl.addFiles(objs);
      });
    };
  };
}

cdsRemoteUploadCtrl.$inject = ["$scope", "$http", "$element", "$q"];

function cdsRemoteUploader() {
  return {
    require: {
      cdsUploaderCtrl: "?^cdsUploader",
      cdsDepositsCtrl: "?^cdsDeposits",
    },
    bindings: {
      remoteMasterReceiver: "@",
      remoteChildrenReceiver: "@",
    },
    controller: cdsRemoteUploadCtrl,
    templateUrl: function ($element, $attrs) {
      return $attrs.template;
    },
  };
}

angular
  .module("cdsDeposit.components")
  .component("cdsRemoteUploader", cdsRemoteUploader());
