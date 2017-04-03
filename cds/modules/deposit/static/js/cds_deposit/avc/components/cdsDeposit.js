function cdsDepositCtrl(
  $scope,
  $q,
  $timeout,
  $interval,
  $sce,
  depositStates,
  depositStatuses,
  depositActions,
  inheritedProperties,
  cdsAPI,
  urlBuilder,
  typeReducer
) {
  var that = this;

  this.depositFormModels = [];

  // The Upload Queue
  this.filesQueue = [];

  // Auto data update timeout
  this.autoUpdateTimeout = null;

  // Checkout
  this.lastUpdated = new Date();

  // Event Listener (only for destroy)
  this.sseEventListener = null;

  // Add depositStatuses to the scope
  this.depositStatuses = depositStatuses;

  // Alerts
  this.alerts = [];

  // Ignore server validation errors for the following fields
  this.noValidateFields = ['description.value'];

  this.previewer = null;

  // Failed subformats
  this.failedSubformatKeys = [];

  Object.defineProperty(this, 'depositType', {
    get: function() {
      return that.master ? 'project' : 'video';
    }
  })

  // FIXME Init stateQueue -  maybe ```Object(depositStatuses).keys()```
  this.stateQueue = {
    PENDING: [],
    STARTED: [],
    FAILURE: [],
    SUCCESS: [],
    REVOKED: [],
  };

  // Initialize stateOrder
  this.stateOrder = angular.copy(depositStates);
  // Initilize stateCurrent
  this.stateCurrent = {};

  this.$onDestroy = function() {
    try {
      // Destroy listener
      that.sseEventListener();
      $timout.cancel(that.autoUpdateTimeout);
    } catch (error) {}
  };

  // The deposit can have the following depositStates
  this.$onInit = function() {
    // Resolve the record schema
    this.cdsDepositsCtrl.JSONResolver(this.schema).then(function(response) {
      that.schema = response.data;
    });

    this.findMasterFileIndex = function() {
      return _.findIndex(that.record._files, {'context_type': 'master'});
    };

    this.initializeStateQueue = function() {
      if (Object.keys(this.record._deposit.state || {}).length > 0) {
        if (
          !Object.keys(this.record._deposit.state).includes('file_download')
        ) {
          that.stateQueue.SUCCESS.push('file_download');
        }
        angular.forEach(this.record._deposit.state, function(value, key) {
          that.stateQueue[value].push(key);
          // Remove it from the state order if
          if ([ 'SUCCESS', 'FAILURE' ].indexOf(value) > -1) {
            that.stateOrder = _.without(that.stateOrder, key);
          }
        });

      } else {
        that.stateQueue.PENDING = angular.copy(depositStates);
        var videoFile = that.record._files[that.findMasterFileIndex()];
        if (videoFile && !videoFile.url) {
          that.stateQueue.PENDING.splice(
            depositStates.indexOf('file_download'),
            1
          );
          that.stateQueue.SUCCESS.push('file_download');
        }
      }

      if (!that.master) {
        $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
      }
      if (this.record._deposit.
          state['file_video_metadata_extraction'] == 'FAILURE') {
        that.failedMetadataExtractionEvent = true;
      }
    };

    function accessElement(obj, elem, value) {
      // Find an element inside an object given a path of properties
      // If value is given, set element to value
      var lastPart, parentObj = obj;
      angular.forEach(ObjectPath.parse(elem), function(part) {
        if (!obj) {
          return null;
        }
        lastPart = part;
        parentObj = obj;
        if (!obj[part] && value) {
          obj[part] = {};
        }
        obj = obj[part];
      });
      if (value) {
        parentObj[lastPart] = value;
      }
      return obj;
    };

    var hasNoProperties = function(obj) {
      return Object.getOwnPropertyNames(obj).length == 0;
    };

    this.inheritMetadata = function() {
      var record = that.record;
      var master = that.cdsDepositsCtrl.master.metadata;

      angular.forEach(inheritedProperties, function(propPath) {
        var inheritedVal = accessElement(master, propPath);
        var ownElement = accessElement(record, propPath);
        if (inheritedVal && !ownElement) {
          accessElement(record, propPath, inheritedVal);
        } else if (ownElement instanceof Array &&
            ownElement.every(hasNoProperties)) {
          var inheritedArray = angular.copy(inheritedVal);
          accessElement(record, propPath, inheritedArray);
        }
      });
    };

    this.getTaskFeedback = function(eventId, taskName, taskStatus) {
      var url = urlBuilder.taskFeedback({ eventId: eventId });
      return cdsAPI.action(url, 'GET').then(function(data) {
        data = _.flatten(data.data, true);
        if (taskName || taskStatus) {
          return data.filter(function (taskInfo) {
            return (!taskName || taskInfo.name == taskName) &&
              (!taskStatus || taskInfo.status == taskStatus);
          });
        } else {
          return data;
        }
      });
    };

    this.restartEvent = function(eventId, taskId) {
      var url = urlBuilder.restartEvent({ taskId: taskId, eventId: eventId });
      return cdsAPI.action(url, 'PUT');
    };

    this.restartMetadataExtraction = function() {
      var metadataFailureIndex = that.stateQueue.FAILURE.
        indexOf('file_video_metadata_extraction');
      if (metadataFailureIndex > -1) {
        that.stateQueue.FAILURE.splice(metadataFailureIndex, 1);
        that.stateQueue.STARTED.push('file_video_metadata_extraction');
        that.record._deposit.state.file_video_metadata_extraction = 'STARTED';
        $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
      }
      var eventId = that.record._files[that.findMasterFileIndex()].
        tags._event_id;
      that.getTaskFeedback(eventId, 'file_video_metadata_extraction',
        'FAILURE').then(function(data) {
        that.failedMetadataExtractionEvent = null;
        data.forEach(function(taskInfo) {
          var eventId = taskInfo.info.payload.event_id;
          var taskId = taskInfo.id;
          that.restartEvent(eventId, taskId).catch(function() {
            that.failedMetadataExtractionEvent = true;
          });
        });
      });
    };

    this.restartFailedSubformats = function(subformatKeys) {
      var eventId = that.record._files[that.findMasterFileIndex()].
        tags._event_id;
      that.failedSubformatKeys = _.difference(that.failedSubformatKeys,
                                              subformatKeys);
      that.record._files[that.findMasterFileIndex()].subformat.forEach(
        function(subformat) {
          if (subformatKeys.includes(subformat.key)) {
            subformat.errored = false;
            subformat.progress = 0;
          }
        });
      var transcodeFailureIndex = that.stateQueue.FAILURE.
                                  indexOf('file_transcode');
      if (transcodeFailureIndex > -1) {
        that.stateQueue.FAILURE.splice(transcodeFailureIndex, 1);
        that.stateQueue.STARTED.push('file_transcode');
        that.record._deposit.state.file_transcode = 'STARTED';
        $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
      }
      that.getTaskFeedback(eventId, 'file_transcode', 'FAILURE')
        .then(function(data) {
        data.filter(function(taskInfo) {
          return subformatKeys.includes(taskInfo.info.payload.key);
        }).forEach(function(taskInfo) {
          var eventId = taskInfo.info.payload.event_id;
          var taskId = taskInfo.id;
          that.restartEvent(eventId, taskId).catch(function() {
            var key = taskInfo.info.payload.key;
            if (!that.failedSubformatKeys.includes(key)) {
              that.failedSubformatKeys.push(key);
            }
          });
        });
      });
    };

    this.initializeStateReported = function() {
      that.stateReporter = {};
      that.presets_finished = [];
      that.presets = [];
      depositStates.map(function(state) {
        that.stateReporter[state] = {
          status: state,
          message: state,
          payload: { percentage: 0 },
        };
      });
    };

    // Calculate the overall total status
    this.calculateStatus = function() {
      if (that.stateQueue.FAILURE.length > 0) {
        return depositStatuses.FAILURE;
      } else if (that.stateQueue.STARTED.length > 0) {
        return depositStatuses.STARTED;
      } else if (that.stateQueue.SUCCESS.length > 0) {
        if (that.stateQueue.SUCCESS.length === depositStates.length) {
          // We are done - stop listening - stop sse
          return depositStatuses.SUCCESS;
        }
        return depositStatuses.STARTED;
      }
      return depositStatuses.PENDING;
    };

    this.videoPreviewer = function(deposit, key) {
      var videoUrl;
      if (deposit && key) {
        videoUrl = urlBuilder.video({
          deposit: deposit,
          key: key,
        });
      } else {
        var videoFile = that.record._files[that.findMasterFileIndex()];
        if (videoFile && videoFile.subformat) {
          var finishedSubformats = videoFile.subformat.filter(function(fmt) {
            return fmt.completed;
          });
          if (finishedSubformats[0]) {
            videoUrl = urlBuilder.video({
              deposit: that.record._deposit.id,
              key: finishedSubformats[0].key,
            });
          }
        }
      }
      if (videoUrl) {
        that.previewer = $sce.trustAsResourceUrl(videoUrl);
      }
    };

    this.subformatSortByKey = function(sub1, sub2) {
      var lengthDiff = sub1.key.length - sub2.key.length;
      if (lengthDiff != 0) {
        return lengthDiff;
      } else {
        return sub1.key.localeCompare(sub2.key);
      }
    };

    this.updateSubformatsList = function(fileOld, fileNew) {
      var subformatsOld = fileOld.subformat || [];
      var subformatsNew = fileNew.subformat || [];

      var keys1 = subformatsOld.map(_.property('key'));
      var keys2 = subformatsNew.map(_.property('key'));
      _.difference(keys2, keys1).forEach(function (newSubformat) {
        subformatsOld.push({key: newSubformat})
      });

      subformatsNew = subformatsNew.sort(that.subformatSortByKey);
      subformatsOld = subformatsOld.sort(that.subformatSortByKey);
      for (var i in subformatsNew) {
        if (subformatsNew[i].progress < subformatsOld.progress) {
          delete subformatsNew[i].progress;
        }
      }

      fileOld.subformat = subformatsOld;
      fileNew.subformat = subformatsNew;
    };

    this.updateDeposit = function(deposit) {
      try {
        for (var i in that.record._files) {
          that.updateSubformatsList(that.record._files[i], deposit._files[i]);
        }
      } catch(error) {
        // Report
      }

      that.record._files = angular.merge(
        [],
        that.record._files,
        deposit._files || []
      );

      // Check for new state
      that.record._deposit.state = angular.merge(
        {},
        that.record._deposit.state,
        deposit._deposit.state || {}
      );
      that.lastUpdated = new Date();
    };

    this.fetchSubformatStatuses = function() {
      var masterIndex = that.findMasterFileIndex();
      if (masterIndex > -1) {
        var masterFile = that.record._files[masterIndex];
        var tags = masterFile.tags;
        if (tags && tags._event_id) {
          var eventId = tags._event_id;
          that.getTaskFeedback(eventId, 'file_transcode')
            .then(function(data) {
              data.filter(function(taskInfo) {
                return taskInfo.status == 'FAILURE';
              }).forEach(function (taskInfo) {
                taskInfo.info.payload.errored = true;
                var key = taskInfo.info.payload.key;
                if (!that.failedSubformatKeys.includes(key)) {
                  that.failedSubformatKeys.push(key);
                }
              });
              var subformatsNew = {
                subformat: data.map(function(task) {
                  var payload = task.info.payload;
                  payload.progress = payload.percentage;
                  return payload;
                })
              };
              that.updateSubformatsList(masterFile, subformatsNew);
              angular.merge(masterFile, subformatsNew);
            });
        }
      }
    };

    // cdsDeposit events

    // Success message
    // Loading message
    // Error message

    // Messages Success
    $scope.$on('cds.deposit.success', function(evt, response) {
      if (evt.currentScope == evt.targetScope) {
        that.alerts = [];
        that.alerts.push({
          message: 'Success!',
          type: 'success'
        });
      }
    });
    // Messages Error
    $scope.$on('cds.deposit.error', function(evt, response) {
      if (evt.currentScope == evt.targetScope) {
        that.alerts = [];
        that.alerts.push({
          message: response.data.message,
          type: 'danger'
        });
      }
    });

    // Initialize state the queue
    this.initializeStateQueue();
    // Initialize state reporter
    this.initializeStateReported();
    // Set the deposit State
    this.depositStatusCurrent = this.calculateStatus();
    // Set stateCurrent - If null -> Waiting SSE events
    that.stateCurrent = that.stateQueue.STARTED[0] || null;
    // Check for previewer
    that.videoPreviewer();
    // Update subformat statuses
    that.fetchSubformatStatuses();
    $interval(that.fetchSubformatStatuses, 30000);

    // Calculate the transcode
    this.updateStateReporter = function(type, data) {
      if (type === 'file_transcode') {
        if (data.state === 'SUCCESS') {
          that.presets_finished.push(data.meta.payload.preset_quality);
          if (that.presets_finished.length === that.presets.length) {
            that.stateQueue.STARTED = _.without(that.stateQueue.STARTED, type);
            that.stateQueue.SUCCESS.push(type);
            // On success remove it from the status order
            that.stateOrder = _.without(that.stateOrder, type);
          }
          if (!that.previewer) {
            that.videoPreviewer(
              data.meta.payload.deposit_id,
              data.meta.payload.key
            );
          }
        } else {
          that.stateReporter[type] = angular.merge(that.stateReporter[type], {
            payload: {
              percentage: that.presets_finished.length / that.presets.length *
                100,
            },
          });
        }
      } else {
        that.stateReporter[type] = angular.copy(data.meta);
      }
    };

    this.stateCurrentCalculate = function(started) {
      var current = _.min(started, function(_state) {
        return _.indexOf(depositStates, _state);
      });
      return _.isEmpty(current) ? null : current;
    };

    // Register related events from sse
    var depositListenerName = 'sse.event.' + this.id;
    this.sseEventListener = $scope.$on(depositListenerName, function(
      evt,
      type,
      data
    ) {
      $scope.$apply(function() {
        // Handle my state
        if (that.stateQueue[data.state].indexOf(type) === -1) {
          var index = that.stateQueue.PENDING.indexOf(type);
          if (index > -1) {
            that.stateQueue.PENDING.splice(index, 1);
          }
          switch (data.state) {
            case 'STARTED':
              that.stateQueue.STARTED.push(type);
              // Callback on started
              that.startedCallback(type, data);
              break;
            case 'FAILURE':
              that.stateQueue.STARTED = _.without(
                that.stateQueue.STARTED,
                type
              );
              that.stateQueue.FAILURE.push(type);
              // On error remove it from the status order
              that.stateOrder = _.without(that.stateOrder, type);
              // Callback on failure
              that.failureCallback(type, data);
              break;
            case 'SUCCESS':
              // FIXME: Better handling
              if (type !== 'update_deposit' && type !== 'file_transcode') {
                that.stateQueue.STARTED = _.without(
                  that.stateQueue.STARTED,
                  type
                );
                that.stateQueue.SUCCESS.push(type);
                // On success remove it from the status order
                that.stateOrder = _.without(that.stateOrder, type);
              }
              // FIXME: Add me later
              // typeReducer.SUCCESS.call(that, type, data)
              that.successCallback(type, data);
              break;
          }
          // The state has been changed update the current
          that.stateCurrent = that.stateCurrentCalculate(that.stateQueue.STARTED);
          // Change the Deposit Status
          that.depositStatusCurrent = that.calculateStatus();
          if (!that.master) {
            $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
          }
        }
        // Update the metadata
        that.updateStateReporter(type, data);
      });

      if (data.meta.payload.key && type === 'file_download') {
        $scope.$broadcast(
          depositListenerName + '.' + data.meta.payload.key,
          type,
          data
        );
      }
      // Check for errors in metadata extraction
      if (type === 'file_video_metadata_extraction') {
        $scope.$broadcast(
          depositListenerName + '.file.metadata_extraction',
          type,
          data
        )
      }
      // Check for errors in the transcoding
      if (data.meta.payload.key && type === 'file_transcode') {
        $scope.$broadcast(
          depositListenerName + '.file.transcoding',
          type,
          data
        )
      }
    });

    this.successCallback = function(type, data) {
      switch (type) {
        case 'file_download':
          // Add the previewer
          /*that.videoPreviewer(
            data.meta.payload.deposit_id,
            data.meta.payload.key
          );*/
          break;
        case 'update_deposit':
          // Update deposit
          that.updateDeposit(data.meta.payload.deposit);
          break;
      }
    };

    this.failureCallback = function(type, data) {
      if (type === 'file_transcode') {
        // Add restart button
      }
    };

    this.startedCallback = function(type, data) {};

    this.displayFailure = function() {
      return that.depositStatusCurrent === that.depositStatuses.FAILURE;
    };

    this.displayPending = function() {
      return that.depositStatusCurrent === that.depositStatuses.PENDING ||
        that.stateCurrent === null &&
          that.depositStatusCurrent !== that.depositStatuses.FAILURE &&
          that.depositStatusCurrent !== that.depositStatuses.SUCCESS;
    };

    this.displayStarted = function() {
      return that.depositStatusCurrent === that.depositStatuses.STARTED &&
        that.stateCurrent !== null;
    };

    this.displaySuccess = function() {
      return that.depositStatusCurrent === that.depositStatuses.SUCCESS;
    };

    this.postSuccessProcess = function(responses) {
      // Get only the latest response (in case of multiple actions)
      var response = (responses[responses.length - 1] || responses).data;
      // Update record
      if (this.updateRecordAfterSuccess) {
        this.record = angular.merge({}, this.record, response.metadata);
      }
      // Update links
      if (this.updateLinksAfterSuccess) {
        this.links = response.links;
      }
    };

    this.postErrorProcess = function(response) {
      // Process validation errors if any
      if (response.data.status === 400 && response.data.errors) {
        var deferred = $q.defer();
        var promise = deferred.promise;
        promise.then(function displayValidationErrors() {
          angular.forEach(response.data.errors, function(value) {
            $scope.$broadcast('cds.deposit.validation.error', value, that.id);
          });
        });
        deferred.resolve();
      }
    };
  };

  this.guessEndpoint = function(action) {
    var link = depositActions[that.depositType][action].link
    if (Object.keys(that.links).indexOf(link) > -1) {
      return that.links[link];
    } else {
      if (that.record._deposit.status === 'published' && !that.master) {
        return urlBuilder.actionVideo({
          deposit: that.record._deposit.id,
          action: action.toLowerCase()
        });
      }
    }
  };

  this.dismissAlert = function(alert) {
    this.alerts.splice(_.indexOf(this.alerts, alert.alert), 1);
  };

  // Do a single action at once
  this.makeSingleAction = function(action, redirect) {
    return this.cdsDepositsCtrl.makeAction(
      that.guessEndpoint(action),
      that.depositType,
      action,
      cdsAPI.cleanData(that.record)
    );
  };

  // Do multiple actions at once
  this.makeMultipleActions = function(actions, redirect) {
    var promises = [];
    var cleanRecord = cdsAPI.cleanData(that.record);
    angular.forEach(
      actions,
      function(action, index) {
        this.push(function() {
          return that.cdsDepositsCtrl.makeAction(
            that.guessEndpoint(action),
            that.depositType,
            action,
            cleanRecord
          );
        });
      },
      promises
    );
    return that.cdsDepositsCtrl.chainedActions(promises);
  };

  this.onSuccessAction = function(response) {
    // Post success process
    that.postSuccessProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.success', response);
    // Make the form pristine again
    _.invoke(that.depositFormModels, '$setPristine');
  };

  this.onErrorAction = function(response) {
    // Post error process
    that.postErrorProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.error', response);
  };

  // Form status
  this.isPristine = function() {
    return that.depositFormModels.every(_.property('$pristine'))
  }

  this.isDirty = function() {
    return that.depositFormModels.some(_.property('$dirty'))
  }

  this.isInvalid = function() {
    return that.depositFormModels.some(_.property('$invalid'))
  }

}

cdsDepositCtrl.$inject = [
  '$scope',
  '$q',
  '$timeout',
  '$interval',
  '$sce',
  'depositStates',
  'depositStatuses',
  'depositActions',
  'inheritedProperties',
  'cdsAPI',
  'urlBuilder',
  'typeReducer',
];

/**
 * @ngdoc component
 * @name cdsDeposit
 * @description
 *   Handles the actions and SSE events for each ``deposit_id``. For each
 *   ``children`` a new ``cds-deposit`` directive will be generated.
 * @attr {String} index - The deposit index in the list of deposits.
 * @attr {Boolean} master - If this deposit is the ``master``.
 * @attr {Boolean} updateRecordAfterSuccess - Update the record after action.
 * @attr {Integer} updateRecordInBackground - Update the record in background.
 * @attr {String} schema - The URI for the deposit type schema.
 * @attr {Object} links - The deposit action links (i.e. ``self``).
 * @attr {Object} record - The record metadata.
 * @example
 *  Example:
 *  <cds-deposit
 *   master="true"
 *   links="$ctrl.master.links"
 *   update-record-after-success="true"
 *   schema="{{ $ctrl.masterSchema }}"
 *   record="$ctrl.master.metadata"
 *  ></cds-deposit>
 */
function cdsDeposit() {
  return {
    transclude: true,
    bindings: {
      index: '=',
      master: '@',
      // Interface related
      updateRecordAfterSuccess: '@',
      updateRecordInBackground: '@?',
      // Deposit related
      id: '=',
      schema: '@',
      record: '=',
      links: '=',
    },
    require: { cdsDepositsCtrl: '^cdsDeposits' },
    controller: cdsDepositCtrl,
    template: '<div ng-transclude></div>',
  };
}

angular.module('cdsDeposit.components').component('cdsDeposit', cdsDeposit());
