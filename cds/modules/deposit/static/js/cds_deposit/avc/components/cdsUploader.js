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

  function updateMasterFileUpload(state, percentage) {
    var masterFile = that.cdsDepositCtrl.findMasterFile();
    if (!masterFile) {
      that.cdsDepositCtrl.stateCurrent = 'file_upload';
      that.cdsDepositCtrl.updateStateReporter('file_upload', {
        payload: {
          percentage: percentage || 0
        }
      }, state);
      that.cdsDepositCtrl.calculateCurrentState();
    }
  }

  /*
   * Updates the file with the success
   */
  function _success(key, data) {
    // Add the necessary flags
    data.percentage = 100;
    data.completed = true;
    that.updateFile(
      key,
      data,
      true
    );
    updateMasterFileUpload('SUCCESS', 100);
  }

  /*
   * Updates the file with the percentage
   */
  function _progress(key, percentage) {
    updateMasterFileUpload('STARTED', percentage);
    that.updateFile(
      key,
      {
        percentage: percentage || 0,
        completed: percentage === 100
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
        percentage: 0
      }
    );
  }

  /*
   * Updates the file with the error
   */
  function _subformatError(key) {
    that.updateSubformat(
      key,
      {
        errored: true,
        percentage: 0
      }
    );
  }

  /*
   * Uploads a local file
   */
  function _local(upload) {
    var promise = $q.defer();
    var args = that.prepareUpload(upload);
    var deposit = that.cdsDepositCtrl;
    deposit.record._deposit.state.file_upload = 'STARTED';
    $scope.$emit('cds.deposit.status.changed', deposit.id, deposit.stateQueue);
    Upload.http(args)
      .then(
        function success(response) {
          deposit.record._deposit.state.file_upload = 'SUCCESS';
          $scope.$emit('cds.deposit.status.changed', deposit.id,
                       deposit.stateQueue);
          _success(
            response.config.data.key,
            response.data
          );
          // Check if needs upload
          var _subpromise;
          if (!upload.key) {
            upload.key = upload.name;
          }
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
            function success(avcResponse) {
              if (avcResponse) {
                that.cdsDepositCtrl.presets = avcResponse.data.presets;
              }
              promise.resolve(response);
            }
          );
        },
        function error(response) {
          updateMasterFileUpload('FAILURE');
          $scope.$emit('cds.deposit.status.changed', deposit.id,
                       deposit.stateQueue);
          promise.reject(response);
        },
        function progress(evt) {
          _progress(
            evt.config.data.key || evt.config.data.name,
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
      function(event, data) {
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
          that.cdsDepositCtrl.presets = response.data.presets;
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
    // Add ``key`` key to be consistent with the backend. JS API for files
    // uses ``name`` instead of ``key``
    return {
      url: that.cdsDepositCtrl.guessEndpoint('BUCKET') + '/' + file.key,
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
      // Do nothing if files array is empty
      if (!_files) {
        return;
      }

      var existingFiles = that.files.map(function(file) {
        return file.key
      });

      angular.forEach(_files, function(file) {
        file.key = file.name;
        file.local = !file.receiver;
      });

      // Exclude files that already exist
      that.duplicateFiles = [];

      var masterFile = that.cdsDepositCtrl.findMasterFile() || {};
      var videoFiles = _.values(that.cdsDepositsCtrl.filterOutFiles(_files)
        .videos);
      // Exclude video files
      _files = _.difference(_files, videoFiles);
      var newMasterFile = videoFiles[0];
      if (newMasterFile) {
        newMasterFile.key = masterFile.key;
      }

      _files = _.reject(_files, function(file) {
        if (existingFiles.includes(file.key)) {
          that.duplicateFiles.push(file.key);
          return true;
        }
        existingFiles.push(file.key);
        return false;
      });

      if (that.cdsDepositCtrl.master) {
        // Add new videos and files to master
        that.cdsDepositsCtrl.addFiles(_files, this.queue);
      } else {
        // Add the files to the list
        if (newMasterFile) {
          that.confirmNewMaster = true;
          that.newMasterName = newMasterFile.name;
          that.newMasterDefer = $q.defer();
          that.newMasterDefer.promise.then(function() {
            var oldMasterIndex = _.findIndex(that.files, {key: masterFile.key});
            that.files.splice(oldMasterIndex, 1);
            that.files.push(newMasterFile);
            that.queue.push(newMasterFile);
            that.upload();
          });
        }
        Array.prototype.push.apply(that.files, _files);
        // Add the files to the queue
        Array.prototype.push.apply(that.queue, _files);
      }
      // Start upload automatically if the option is selected
      if (that.autoStartUpload) {
        that.upload();
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
        // Loading
        that.loading = true;
        return that.uploader()
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
              that.cdsDepositCtrl.waitingUpload = false;
              that.cdsDepositCtrl.loading = false;
              that.loading = false;
            }
          );
      } else {
        // Go ahead no uploads
        that.cdsDepositCtrl.waitingUpload = false;
        return $q.resolve();
      }
    }
  }

  this.$postLink = function() {
    // Upload video file when creating a new deposit
    if (!that.cdsDepositCtrl.master) {
      that.cdsDepositCtrl.waitingUpload = true;
      that.cdsDepositCtrl.loading = true;
      $timeout(function () {
        that.cdsDepositsCtrl.lastVideoUpload =
          that.cdsDepositsCtrl.lastVideoUpload.finally(function() {
          return that.upload();
        });
      }, 1500);
    }
  }

  this.findFileIndex = function(files, key) {
    return _.indexOf(
      files,
      _.find(that.files, {key: key})
    );
  }

  this.updateFile = function(key, data, force) {
    var index = this.findFileIndex(that.files, key);
    if (index != -1) {
      if (force === true) {
        this.files[index] = angular.copy(data);
        return;
      }

      angular.merge(
        this.files[index],
        data || {}
      );
    }
  }

  this.updateSubformat = function(key, data) {
    // Find master
    var master = that.cdsDepositCtrl.findMasterFile();
    if (master) {
      // Find the index of the subformat
      var subformats = master.subformat;
      var index = _.findIndex(subformats, {'key': key});
      if (index > -1 && !subformats[index].errored) {
        subformats[index] = angular.merge(
          {},
          subformats[index],
          data
        );
      } else if (index == -1) {
        subformats.push(angular.merge(
          { key: key },
          data
        ));
      }
    }
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

  this.allFinished = function() {
    return (that.files || []).every(function(file) {
      return file.completed;
    });
  }
}

cdsUploaderCtrl.$inject = [
  '$scope',
  '$q',
  'Upload',
  '$http',
  '$timeout',
  'urlBuilder',
  'jwt'
];

function cdsUploader() {
  return {
    transclude: true,
    bindings: {
      files: '=',
      filterFiles: '=',
      remoteMasterReceiver: '@?',
      autoStartUpload: '=?'
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
