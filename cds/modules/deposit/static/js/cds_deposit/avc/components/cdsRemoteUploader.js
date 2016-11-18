function cdsRemoteUploader() {
  return {
    require: {
      cdsDepositsCtrl: '?^cdsDeposits',
      cdsDepositCtrl: '?^cdsDeposit'
    },
    bindings: {
      remoteReceiver: '@',
      dropboxEnabled: '<',
      dropboxAppKey: '@',
      dropboxSelector: '@',
      files: '=',
    },
    controller: function($scope, $http, $element) {
      var that = this;
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
              if (that.files) {
                that.cdsDepositCtrl.filesQueue.push.apply(
                  that.cdsDepositCtrl.filesQueue, _files);
                that.files.push.apply(that.files, _files);
                $scope.$apply();
              } else {
                that.cdsDepositsCtrl.initDeposit(_files);
              }
            },
            linkType: 'direct'
          });
          $element[0].querySelector(this.dropboxSelector).appendChild(button);
        } else {
          $scope.dropboxError = 'Dropbox dropins.js is not loaded';
        }
      }

      $scope.startUrlUpload = function(url) {
        var parser = document.createElement('a');
        parser.href = url;
        var name = parser.pathname.split('/').pop();
        var obj = {
          key: name,
          name: name,
          receiver: that.remoteReceiver,
          url: url
        };
        if (that.files) {
          that.cdsDepositCtrl.filesQueue.push(obj);
          that.files.push(obj);
        } else {
          that.cdsDepositsCtrl.initDeposit([obj]);
        }
      };
    },

    templateUrl: function($element, $attrs) {
      return $attrs.template;
    }
  }
}

angular.module('cdsDeposit.components')
  .component('cdsRemoteUploader', cdsRemoteUploader());
