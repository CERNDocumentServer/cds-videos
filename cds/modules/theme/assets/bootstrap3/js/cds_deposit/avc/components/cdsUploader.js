import angular from "angular";
import _ from "lodash";

import { getCookie } from "../../../getCookie";

function cdsUploaderCtrl(
  $scope,
  $q,
  Upload,
  $http,
  $timeout,
  urlBuilder,
  toaster,
  isoLanguages
) {
  var that = this;

  // Is the uploader loading
  this.loading = false;
  // Do we have any errors
  this.errors = [];
  // The ongoing uploads
  this.uploading = [];

  function preventBrowserClose(e) {
    // Cancel the event
    e.preventDefault();
    // Chrome requires returnValue to be set
    e.returnValue = "";
  }

  function updateMasterFileUpload(state, percentage) {
    var masterFile = that.cdsDepositCtrl.findMasterFile();
    if (!masterFile) {
      that.cdsDepositCtrl.currentStartedTaskName = "file_upload";
      that.cdsDepositCtrl.updateStateReporter(
        "file_upload",
        {
          payload: {
            percentage: percentage || 0,
          },
        },
        state
      );
      that.cdsDepositCtrl.calculateCurrentDepositStatus();
    }
  }

  /*
   * Updates the file with the success
   */
  function _success(key, data) {
    // Add the necessary flags
    data.percentage = 100;
    data.completed = true;
    if (data.tags) {
      // put the tags outside
      data = angular.merge({}, data, data.tags || {});
    }
    that.updateFile(key, data, true);
    updateMasterFileUpload("SUCCESS", 100);
  }

  /*
   * Updates the file with the percentage
   */
  function _progress(key, percentage) {
    updateMasterFileUpload("STARTED", percentage);
    that.updateFile(key, {
      percentage: percentage || 0,
      completed: percentage === 100,
    });
  }

  /*
   * Updates the file with the error
   */
  function _error(key) {
    that.updateFile(key, {
      status_failure: true,
      percentage: 0,
    });
  }

  /*
   * Updates the file with the error
   */
  function _subformatError(key) {
    that.updateSubformat(key, {
      status_failure: true,
      percentage: 0,
    });
  }

  /*
   * Uploads a local file
   */
  function _local(upload) {
    var promise = $q.defer();
    var args = that.prepareUpload(upload);
    var deposit = that.cdsDepositCtrl;
    deposit.record._cds.state.file_upload = "STARTED";
    $scope.$emit("cds.deposit.status.changed", deposit.id, deposit.stateQueue);
    Upload.http(args).then(
      function success(response) {
        deposit.record._cds.state.file_upload = "SUCCESS";
        $scope.$emit(
          "cds.deposit.status.changed",
          deposit.id,
          deposit.stateQueue
        );
        _success(response.config.data.key, response.data);
        // Check if needs upload
        var _subpromise;
        if (!upload.key) {
          upload.key = upload.name;
        }
        if (
          !upload.isAdditional &&
          that.cdsDepositsCtrl.isVideoFile(upload.key)
        ) {
          _subpromise = Upload.http(_startWorkflow(upload, response));
        } else {
          var d = $q.defer();
          d.resolve();
          _subpromise = d.promise;
        }
        _subpromise.then(function success(avcResponse) {
          if (avcResponse) {
            that.cdsDepositCtrl.presets = avcResponse.data.presets;
          }
          that.cdsDepositsCtrl.fetchRecord();
          promise.resolve(response);
        });
      },
      function error(response) {
        updateMasterFileUpload("FAILURE");
        $scope.$emit(
          "cds.deposit.status.changed",
          deposit.id,
          deposit.stateQueue
        );
        promise.reject(response);
      },
      function progress(evt) {
        _progress(
          evt.config.data.key || evt.config.data.name,
          parseInt((100.0 * evt.loaded) / evt.total, 10)
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
    var deposit = that.cdsDepositCtrl;
    $http(args).then(
      function success(response) {
        deposit.presets = response.data.presets;
        deposit.waitingUpload = false;
        that.cdsDepositsCtrl.fetchRecord();

        const checkDownloadTaskStatus = () => {
          deposit.getTaskFeedback(response.data.tags.flow_id).then(
            function (data) {
              var allFlowsTasksByName = _.groupBy(data, "name");
              const fileDownloadTask = allFlowsTasksByName?.file_download[0];
              if (["FAILED", "SUCCESS"].indexOf(fileDownloadTask.status) > -1) {
                clearInterval(intervalId);
                that.cdsDepositsCtrl.fetchRecord();
                deposit.fetchFlowTasksStatuses();
                // Stop loading
                deposit.loading = false;
                that.loading = false;
              }
            },
            function error(response) {
              deposit.waitingUpload = false;
              that.cdsDepositsCtrl.fetchRecord();
              console.error(response);
            }
          );
        };
        const intervalId = setInterval(checkDownloadTaskStatus, 3000);
      },
      function error(response) {
        deposit.waitingUpload = false;
        that.cdsDepositsCtrl.fetchRecord();
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
    var _headers = angular.merge(
        {},
        {
          "Content-Type": (file.type || "").indexOf("/") > -1 ? file.type : "",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        file.headers || {}
      ),
      url = urlBuilder.bucketVideo({
        bucket: that.cdsDepositCtrl.record._buckets.deposit,
      });

    return {
      url: url + "/" + file.key,
      method: "PUT",
      headers: _headers,
      data: file,
    };
  }

  /*
   * Start workflow
   */
  function _prepareRemoteFileWebhooks(file) {
    return {
      url: file.receiver,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: {
        uri: file.url,
        key: file.key,
        bucket_id: that.cdsDepositCtrl.record._buckets.deposit,
        deposit_id: that.cdsDepositCtrl.record._deposit.id,
      },
    };
  }

  /*
   * Prepare http request of Local File Upload with Webhooks
   */
  function _startWorkflow(file, response) {
    return {
      method: "POST",
      url: that.remoteMasterReceiver,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      data: {
        version_id: response.data.version_id,
        key: file.key,
        bucket_id: that.cdsDepositCtrl.record._buckets.deposit,
        deposit_id: that.cdsDepositCtrl.record._deposit.id,
      },
    };
  }

  // On Component init
  this.$onInit = function () {
    // The Uploader queue
    this.queue = [];

    // Add any files in the queue that are not completed
    Array.prototype.push.apply(
      this.queue,
      _.reject(this.files, { completed: true })
    );

    this.addFiles = function (_files, invalidFiles, extraHeaders) {
      // Do nothing if files array is empty
      if (!_files) {
        return;
      }
      // Remove any invalid files
      _files = _.difference(_files, invalidFiles || []);

      // Filter out files without a valid MIME type or with zero size
      _files = _files.filter((file) => {
        if (!file.type || file.type.trim() === "") {
          toaster.pop(
            "warning",
            "Invalid File Type",
            `The file ${file.name} has no valid type.`
          );
          return false; // Exclude invalid files
        }

        if (!file.size || file.size === 0) {
          toaster.pop(
            "warning",
            "Empty File",
            `The file ${file.name} is empty and cannot be uploaded.`
          );
          return false; // Exclude zero-size files
        }

        return true;
      });

      // Make sure they have proper metadata
      angular.forEach(_files, function (file) {
        file.key = file.name;
        file.local = !file.receiver;
        file.isAdditional = true;
        // Add any extra paramemters to the files
        if (extraHeaders) {
          file.headers = extraHeaders;
        }
        file.headers = {
          "X-Invenio-File-Tags": "context_type=additional_file",
        };
      });

      // Find if any of the existing files has been replaced
      // (file with same filename), and if yes remove it from the existing
      // file list (aka from the interface).
      _files = _.each(_files, function (file) {
        // Remove the existing file from the list
        _.remove(that.files, function (_f) {
          return _f.key === file.key;
        });
      });

      if ((invalidFiles || []).length > 0) {
        // Push a notification
        toaster.pop({
          type: "error",
          title:
            "Invalid file(s) for " +
            (that.cdsDepositCtrl.record.title.title || "video."),
          body: _.map(invalidFiles, "name").join(", "),
          bodyOutputType: "trustedHtml",
        });
      }

      // Add files to the list
      Array.prototype.push.apply(that.files, _files);
      // Add the files to the queue
      Array.prototype.push.apply(that.queue, _files);

      // Start upload automatically if the option is selected
      if (that.autoStartUpload) {
        that.upload();
      }
    };

    this.replaceMasterFile = function (_files, invalidFiles) {
      // Do nothing if files array is empty
      if (!_files) {
        return;
      }
      // Remove any invalid files
      _files = _.difference(_files, invalidFiles || []);
      // Make sure they have proper metadata
      angular.forEach(_files, function (file) {
        file.key = file.name;
        file.local = !file.receiver;
      });

      // Add the files to the list
      var masterFile = that.cdsDepositCtrl.findMasterFile() || {};
      var videoFiles = _.values(
        that.cdsDepositsCtrl.filterOutFiles(_files).videos
      );

      if ((invalidFiles || []).length > 0) {
        // Push a notification
        toaster.pop({
          type: "error",
          title:
            "Invalid file(s) for " +
            (that.cdsDepositCtrl.record.title.title || "video."),
          body: _.map(invalidFiles, "name").join(", "),
          bodyOutputType: "trustedHtml",
        });
      }

      if (!that.cdsDepositCtrl.master) {
        // Check for new master file
        var newMasterFile = videoFiles[0];
        if (newMasterFile) {
          newMasterFile.key = masterFile.key;
          that.confirmNewMaster = true;
          that.newMasterName = newMasterFile.name;
          that.newMasterDefer = $q.defer();
          // Update how many times the master file has been replaced.
          // It is useful to indicate in the UI how many times
          // the file has been changed. Note is only used for UI, the number
          // means nothing.
          var masterFileVersion =
            masterFile.tags && masterFile.tags.times_replaced
              ? parseInt(masterFile.tags.times_replaced) + 1
              : 1;
          // Add how many times has been changed tag
          newMasterFile.headers = {
            "X-Invenio-File-Tags": "times_replaced=" + masterFileVersion,
          };
          that.newMasterDefer.promise.then(function () {
            // FIXME masterFile.key is undefined !?!
            var old_master = that.files.splice(
              _.findIndex(that.files, { key: masterFile.key }),
              1
            );
            that.files.push(newMasterFile);
            that.queue.push(newMasterFile);
            // Upload the video file
            var old_flow_id = old_master[0]["tags"]["flow_id"];
            that.cdsDepositCtrl.previewer = null;
            that.upload();
          });
        }
      }
    };

    // Prepare file request
    this.prepareUpload = function (file) {
      return file.receiver
        ? _prepareRemoteFileWebhooks(file)
        : _prepareLocalFile(file);
    };

    this.prepareDelete = function (url) {
      // add the logic here
      var args = {
        url: url,
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      };
      return args;
    };

    this.uploader = function () {
      var defer = $q.defer();
      var data = [];
      function _chain(upload) {
        // Get the arguments
        var promise = upload.receiver ? _remote(upload) : _local(upload);
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
    };

    this.upload = function () {
      if (that.queue.length > 0) {
        // prevent user closes the browser by showing a warning
        window.addEventListener("beforeunload", preventBrowserClose);
        // Loading
        that.loading = true;
        return that
          .uploader()
          .then(
            function success(response) {
              // Success uploading notification
              toaster.pop({
                type: "info",
                title: "The file(s) has been successfully uploaded.",
                body: (_.map(response, "data.key") || []).join(", "),
                bodyOutputType: "trustedHtml",
              });
            },
            function error(response) {
              // Inform the parents
              $scope.$emit("cds.deposit.error", response);
              // Check if the response contains the error message
              if (
                response.status === 400 &&
                response.data &&
                response.data.message
              ) {
                toaster.pop({
                  type: "error",
                  title: response.data.message,
                  bodyOutputType: "trustedHtml",
                });
              } else {
                // Error uploading notification
                toaster.pop({
                  type: "error",
                  title: "Error uploading the file(s).",
                  body: (_.map(response, "config.data.key") || []).join(", "),
                  bodyOutputType: "trustedHtml",
                });
              }
            }
          )
          .finally(function done() {
            // Stop loading
            that.cdsDepositCtrl.waitingUpload = false;
            that.cdsDepositCtrl.loading = false;
            that.loading = false;
            window.removeEventListener("beforeunload", preventBrowserClose);
          });
      } else {
        // Go ahead no uploads
        that.cdsDepositCtrl.waitingUpload = false;
        return $q.resolve();
      }
    };
  };

  this.$postLink = function () {
    // Upload video file when creating a new deposit
    if (!that.cdsDepositCtrl.master) {
      that.cdsDepositCtrl.waitingUpload = true;
      that.cdsDepositCtrl.loading = true;
      $timeout(function () {
        that.upload();
      }, 1500);
    }
  };

  this.findFileIndex = function (files, key) {
    return _.indexOf(files, _.find(that.files, { key: key }));
  };

  this.validateSubtitles = function (_file) {
    // Check if the filename matches the pattern and is a valid ISO language
    // i.e. jessica_jones-en.vtt
    var match = _file.name.match(/(?:.+)[_|-]([a-zA-Z]{2}).vtt/) || [];
    return match.length > 1 && match[1] in isoLanguages;
  };

  this.updateFile = function (key, data, force) {
    var index = this.findFileIndex(that.files, key);
    if (index != -1) {
      if (force === true) {
        this.files[index] = angular.copy(data);
        return;
      }

      angular.merge(this.files[index], data || {});
    }
  };

  this.updateSubformat = function (key, data) {
    // Find master
    var master = that.cdsDepositCtrl.findMasterFile();
    if (master) {
      // Find the index of the subformat
      var subformats = master.subformat;
      var index = _.findIndex(subformats, { key: key });
      if (index > -1 && !subformats[index].status_failure) {
        subformats[index] = angular.merge({}, subformats[index], data);
      } else if (index == -1) {
        subformats.push(angular.merge({ key: key }, data));
      }
    }
  };

  this.abort = function () {
    // Abort the upload
  };

  this.remove = function (key) {
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
        that.files[index].links.version || that.files[index].links.deleteFile
      );
      $http(args).then(
        function success(response) {
          // Remove the file from the list
          that.files.splice(index, 1);
          // Success uploading notification
          toaster.pop({
            type: "success",
            title: "The file has been succesfuly deleted.",
            bodyOutputType: "trustedHtml",
          });
        },
        function error(response) {
          // Inform the parents
          $scope.$emit("cds.deposit.error", response);
          // Error uploading notification
          toaster.pop({
            type: "error",
            title: "Error deleting the file.",
            bodyOutputType: "trustedHtml",
          });
        }
      );
    }
  };

  this.thumbnailPreview = function (frame) {
    return urlBuilder.iiif({
      deposit: frame.bucket_id,
      key: frame.key,
      res: "150,100",
      version_id: frame.version_id,
    });
  };

  this.allFinished = function () {
    return (that.files || []).every(function (file) {
      return file.completed;
    });
  };
}

cdsUploaderCtrl.$inject = [
  "$scope",
  "$q",
  "Upload",
  "$http",
  "$timeout",
  "urlBuilder",
  "toaster",
  "isoLanguages",
];

function cdsUploader() {
  return {
    transclude: true,
    bindings: {
      files: "=",
      filterFiles: "=",
      remoteMasterReceiver: "@?",
      autoStartUpload: "=?",
    },
    require: {
      cdsDepositCtrl: "^cdsDeposit",
      cdsDepositsCtrl: "^cdsDeposits",
    },
    controller: cdsUploaderCtrl,
    templateUrl: [
      "$element",
      "$attrs",
      function ($element, $attrs) {
        return $attrs.template;
      },
    ],
  };
}

angular.module("cdsDeposit.components").component("cdsUploader", cdsUploader());
