function cdsUploaderCtrl($scope, $q, Upload, $http, $timeout) {
  var that = this;

  // Is the uploader loading
  this.loading = false;
  // Do we have any errors
  this.errors = [];
  // The ongoing uploads
  this.uploading = [];

  // On Component init
  this.$onInit = function() {
    // The Uploader queue
    this.queue = [];

    // Add any files in the queue that are not completed
    Array.prototype.push.apply(this.queue, _.reject(this.files, {completed: true}));

    this.addFiles = function(_files) {
      var existingFiles = that.files.map(function(file) {
        return file.key
      });
      angular.forEach(_files, function(file) {
        // GRRRRRRRRRRR :(
        file.key = file.name;
        // Mark the file as local
        file.local = true;
      });
      // Exclude files that already exist
      _files = _.reject(_files, function(file) {
        return existingFiles.includes(file.key);
      });
      if (that.cdsDepositCtrl.master) {
        // Add new videos and files to master
        that.cdsDepositsCtrl.addFiles(_files, this.queue);
      } else {
        var videoFiles = _.values(that.cdsDepositsCtrl.filterOutFiles(_files).videos);
        // Exclude video files
        _files = _.difference(_files, videoFiles);
        // Add the files to the list
        Array.prototype.push.apply(that.files, _files);
        // Add the files to the queue
        Array.prototype.push.apply(that.queue, _files);
      }
    };


    // Prepare file request
    this.prepareUpload = function(file) {
      var args;
      if (file.receiver) {
        args = {
          url: file.receiver,
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          data: {
            uri: file.url,
            key: file.key,
            bucket_id: that.cdsDepositCtrl.record._buckets.deposit,
            deposit_id: that.cdsDepositCtrl.record._deposit.id,
            sse_channel: '/api/deposits/' + that.cdsDepositsCtrl.master.metadata._deposit.id + '/sse',
          }
        };
      } else {
        args = {
          url: that.cdsDepositCtrl.links.bucket + '/' + file.key,
          method: 'PUT',
          headers: {
            'Content-Type': (file.type || '').indexOf('/') > -1 ? file.type : ''
          },
          data: file
        };
      }
      return args;
    };

    this.prepareDelete = function(url) {
      // add the logic here
      var args = {
        url:  url,
        method: 'DELETE'  ,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      return args;
    }

    this.uploader = function() {
      var defer = $q.defer();
      var data = [];
      function _chain(upload) {
        var downloadPromise;
        var args = that.prepareUpload(upload);
        if (!upload.receiver) {
          downloadPromise = Upload.http(args).then(
            function success(response) {
              // Update the file with status
              response.data.completed = true;
              response.data.progress = 100;
              that.updateFile(
                response.config.data.key,
                response.data,
                true
              );
              data.push(response.data);
            },
            function error(response) {
              // Throw an error
              defer.reject(response);
            },
            function progress(evt) {
              var progress = parseInt(100.0 * evt.loaded / evt.total, 10);
              that.cdsDepositCtrl.progress = progress;
              // Update the file with status
              that.updateFile(
                evt.config.data.key,
                {
                  progress: progress
                }
              );
            }
          );
        } else {
          Upload.http(args);
          var fileListenerName = 'sse.event.' + that.cdsDepositCtrl.record._deposit.id + '.' + upload.key;
          $scope.$on(fileListenerName, function(event, type, data) {
            var updateObj, progress;
            var payload = data.meta.payload;
            if (data.state != 'FAILURE') {
              progress = payload.percentage;
              var completed = progress == 100;
              updateObj = {
                progress: progress,
                completed: completed
              };
            } else {
              updateObj = {
                errored: true
              };
            }
            console.warn('PROGRESS', progress);
            if (progress) {
              that.cdsDepositCtrl.progress = progress;
            }
            $timeout(function() {
              that.updateFile(payload.key, updateObj);
            }, 0);
          }, false);
          var deferred = $q.defer();
          deferred.resolve();
          downloadPromise = deferred.promise;
        }
        downloadPromise.finally(function finish(evt) {
          if (that.queue.length > 0) {
            return _chain(that.queue.shift());
          } else {
            defer.resolve(data);
          }
        });
      }
      _chain(that.queue.shift());
      return defer.promise;
    }

    this.upload = function() {
      if (that.queue.length > 0) {
        // Start loading
        $scope.$emit('cds.deposit.loading.start');
        that.cdsDepositCtrl.loading = true;
        // Start local loading
        that.loading = true;
        that.uploader()
        .then(
          function success(response) {
          },
          function error(response) {
            // Inform the parents
            $scope.$emit('cds.deposit.error', response);
          }
        ).finally(
          function done() {
            // Stop loading
            $scope.$emit('cds.deposit.loading.stop');
            that.cdsDepositCtrl.loading = false;
            // Local loading
            that.loading = false;
          }
        );
      }
    }
  }

  this.$postLink = function() {
    // Upload video file when creating a new deposit
    if (!this.cdsDepositCtrl.master) {
      this.upload();
    }
  }

  this.findFileIndex = function(files, key) {
    return _.indexOf(
      files,
      _.findWhere(that.files, {key: key})
    );
  }

  this.updateFile = function(key, data, force) {
    var index = this.findFileIndex(that.files, key);
    if (force === true) {
      this.files[index] = angular.copy(data);
      return;
    }

    angular.merge(
      this.files[index],
      data || {}
    );
  }

  this.abort = function() {
    // Abort the upload
  };

  this.remove = function(key) {
    // Find the file index
    var index = this.findFileIndex(that.files, key);

    if (this.files[index].links === undefined) {
      // Remove the file from the list
      that.files.splice(index, 1);
      // Find the file's index in the queue
      var q_index = this.findFileIndex(that.queue, key);
      // remove the file from the queue
      that.queue.splice(q_index, 1);
    } else {
      var args = that.prepareDelete(
        that.files[index].links.version || that.files[index].links.self
      );
      $http(args)
      .then(
        function success() {
          // Remove the file from the list
          that.files.splice(index, 1);
        },
        function error(error) {
          // Inform the parents
          $scope.$emit('cds.deposit.error', response);
        }
      );
    }
  };
}

cdsUploaderCtrl.$inject = ['$scope', '$q', 'Upload', '$http', '$timeout'];

function cdsUploader() {
  return {
    transclude: true,
    bindings: {
      files: '=',
      filterFiles: '=',
    },
    require: {
      cdsDepositCtrl: '^cdsDeposit',
      cdsDepositsCtrl: '^cdsDeposits'
    },
    controller: cdsUploaderCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    }
  }
}

angular.module('cdsDeposit.components')
  .component('cdsUploader', cdsUploader());
