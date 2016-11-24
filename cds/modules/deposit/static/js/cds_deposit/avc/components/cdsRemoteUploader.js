function cdsRemoteUploadCtrl($scope, $http, $element, $q) {
  var that = this;

  this.$onInit = function() {
    // Initialize dropbox dropin if enabled
    if (this.dropboxEnabled) {
      if (typeof Dropbox !== 'undefined') {
        Dropbox.appKey = this.dropboxAppKey;
        var button = Dropbox.createChooseButton({
          success: function (files) {
            var _files = files.map(function (file) {
              return {
                key: file.name,
                name: file.name,
                size: file.bytes,
                receiver: that.remoteReceiver,
                url: file.link
              };
            });
            var ctrl = that.cdsUploaderCtrl || that.cdsDepositsCtrl;
            ctrl.addFiles(_files);
            $scope.$apply();
          },
          linkType: 'direct'
        });
        $element[0].querySelector(this.dropboxSelector).appendChild(button);
      } else {
        $scope.dropboxError = 'Dropbox dropins.js is not loaded';
      }
    }

    $scope.startUrlUpload = function (url) {
      // Use an a element to parse the URL
      var parser = document.createElement('a');
      parser.href = url;
      var name = parser.pathname.split('/').pop();
      var obj = {
        key: name,
        name: name,
        receiver: that.remoteReceiver,
        url: url
      };
      var sizePromise;
      // Retrieve the file size if the protocol is http/s
      if (url.startsWith('http')) {
        sizePromise = $http.head(url).then(function (response) {
          obj.size = response.headers('content-length');
        });
      } else {
        sizePromise = $q.resolve();
      }
      sizePromise.finally(function () {
        var ctrl = that.cdsUploaderCtrl || that.cdsDepositsCtrl;
        ctrl.addFiles([obj]);
      });
    };
  };
}

cdsRemoteUploadCtrl.$inject = ['$scope', '$http', '$element', '$q'];

function cdsRemoteUploader() {
  return {
    require: {
      cdsUploaderCtrl: '?^cdsUploader',
      cdsDepositsCtrl: '?^cdsDeposits'
    },
    bindings: {
      remoteReceiver: '@',
      dropboxEnabled: '<',
      dropboxAppKey: '@',
      dropboxSelector: '@'
    },
    controller: cdsRemoteUploadCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    }
  }
}

angular.module('cdsDeposit.components')
  .component('cdsRemoteUploader', cdsRemoteUploader());
