function cdsUploaderCtrl($scope, $q, Upload, $http, $timeout, urlBuilder) {
  var that = this;

  // Is the uploader loading
  this.loading = false;
  // Do we have any errors
  this.errors = [];
  // The ongoing uploads
  this.uploading = [];
  // The SSE listener
  this.sseEventListener = null;

  this.$onDestroy = function() {
    try {
      // Destroy listener
      that.sseEventListener();
    } catch(error) {
      // Ok probably already done
    }
  }

  /*
   * Updates the file with the success
   */
  function _success(key, data) {
    // Add the necessary flags
    data.progress = 100;
    data.completed = true;
    that.updateFile(
      key,
      data,
      true
    );
  }

  /*
   * Updates the file with the percentage
   */
  function _progress(key, progress) {
    that.updateFile(
      key,
      {
        progress: progress || 0,
        completed: progress === 100
      }
    );
  }

  /*
   * Updates the file with the error
   */
  function _error(key) {
    that.updateFile(
      key,
      {
        errored: true,
        progress: 0
      }
    );
  }

  /*
   * Uploads a local file
   */
  function _local(upload) {
    var promise = $q.defer();
    var args = that.prepareUpload(upload);
    Upload.http(args)
      .then(
        function success(response) {
          _success(
            response.config.data.key,
            response.data
          );
          // Check if needs upload
          var _subpromise;
          if (that.cdsDepositsCtrl.isVideoFile(upload.key)) {
            _subpromise = Upload.http(
              _prepareLocalFileWebhooks(upload, response)
            );
          } else {
            var d = $q.defer();
            d.resolve();
            _subpromise = d.promise;
          }
          _subpromise.then(
            function success() {;
              promise.resolve(response);
            }
          );
        },
        function error(response) {
          promise.reject(response);
        },
        function progress(evt) {
          _progress(
            evt.config.data.key,
            parseInt(100.0 * evt.loaded / evt.total, 10)
          );
        }
      );
    return promise.promise;
  }

  /*
   * Uploads a remote file
   */
  function _remote(upload) {
    var args = that.prepareUpload(upload);
    var promise = $q.defer();
    // Prepare the listener
    that.sseEventListener = $scope.$on(
      'sse.event.' + that.cdsDepositCtrl.record._deposit.id + '.' + upload.key,
      function(event, type, data) {
        switch (data.state) {
          case 'FAILURE':
            _error(upload.key);
            break;
          case 'SUCCESS':
            _success(upload.key, data.meta.payload);
            promise.resolve(data.meta.payload);
            // Turn off that listener we don't need it any more
            that.sseEventListener();
          default:
            _progress(
              upload.key,
              data.meta.payload.percentage
            );
        }
      });
    $http(args)
      .then(
        function success(response) {
        },
        function error(response) {
          promise.reject(response);
        }
      );
    return promise.promise;
  }

  /*
   * Prepare http request of Local File Upload without Webhooks
   */
  function _prepareLocalFile(file) {
    return {
      url: that.cdsDepositCtrl.links.bucket + '/' + file.key,
      method: 'PUT',
      headers: {
        'Content-Type': (file.type || '').indexOf('/') > -1 ? file.type : ''
      },
      data: file
    };
  };

  /*
   * Prepare http request of Remote File Upload with Webhooks
   */
  function _prepareRemoteFileWebhooks(file) {
    return {
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
  }

  /*
   * Prepare http request of Local File Upload with Webhooks
   */
  function _prepareLocalFileWebhooks(file, response) {
    return {
      method: 'POST',
      url: that.remoteMasterReceiver,
      headers: {
        'Content-Type': 'application/json'
      },
      data: {
        version_id: response.data.version_id,
        key: file.key,
        bucket_id: that.cdsDepositCtrl.record._buckets.deposit,
        deposit_id: that.cdsDepositCtrl.record._deposit.id,
        sse_channel: '/api/deposits/' + that.cdsDepositsCtrl.master.metadata._deposit.id + '/sse',
      }
    }
  }

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
        file.key = file.name;
        file.local = (file.receiver) ? false : true;
      });

      // Exclude files that already exist
      _files = _.reject(_files, function(file) {
        if (existingFiles.includes(file.key)) {
          return true;
        }
        existingFiles.push(file.key);
        return false;
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
      return (file.receiver) ? _prepareRemoteFileWebhooks(file) : _prepareLocalFile(file);
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
        // Get the arguments
        var promise = (upload.receiver) ? _remote(upload) : _local(upload);
        promise.then(
          function success(response) {
            data.push(response);
            // Check for the next one
            if (that.queue.length > 0) {
              return _chain(that.queue.shift());
            } else {
              defer.resolve(data);
            }
          },
          function error(response) {
            defer.reject(response);
          }
        );
      }
      _chain(that.queue.shift());
      return defer.promise;
    }

    this.upload = function() {
      if (that.queue.length > 0) {
        // FIXME: LOADING
        // Start loading
        $scope.$emit('cds.deposit.loading.start');
        // Start local loading
        that.cdsDepositCtrl.loading = true;
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
              // FIXME: LOADING
              $scope.$emit('cds.deposit.loading.stop');
              that.cdsDepositCtrl.loading = false;
              that.loading = false;
            }
          );
      }
    }
  }

  this.$postLink = function() {
    // Upload video file when creating a new deposit
    if (!this.cdsDepositCtrl.master) {
      $timeout(function () {
        that.upload();
      }, 1500);
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

  this.thumbnailPreview = function(key) {
    return urlBuilder.iiif({
      deposit: that.cdsDepositCtrl.record._buckets.deposit,
      key: key,
      res: '150,100'
    });
  };

  this.getFrames = function() {
    return (that.files || []).reduce(function (frames, next) {
      return frames || next.frame;
    }, null);
  };

  this.getSubformats = function() {
    return (that.files || []).reduce(function (videos, next) {
      return videos || next.video;
    }, null);
  };

  this.allFinished = function() {
    return (that.files || []).every(function(file) {
      return file.completed;
    });
  }
}

cdsUploaderCtrl.$inject = ['$scope', '$q', 'Upload', '$http', '$timeout',
                           'urlBuilder'];

function cdsUploader() {
  return {
    transclude: true,
    bindings: {
      files: '=',
      filterFiles: '=',
      remoteMasterReceiver: '@?'
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
