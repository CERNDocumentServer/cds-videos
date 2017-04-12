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
  typeReducer,
  localStorageService
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

  // Metadata information to automatically fill form
  this.metadataToFill = false;

  // Ignore server validation errors for the following fields
  this.noValidateFields = ['description.value'];

  this.previewer = null;

  // Failed subformats
  this.failedSubformatKeys = [];

  // Deposit type property
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

  this.taskState = {};

  // Initilize stateCurrent
  this.stateCurrent = {};

  this.$onDestroy = function() {
    try {
      // Clear local storage
      that.cleanLocalStorage();

      // Destroy listener
      that.sseEventListener();
      $interval.cancel(that.fetchStatusInterval);
      $timeout.cancel(that.autoUpdateTimeout);
    } catch (error) {}
  };

  // The deposit can have the following depositStates
  this.$onInit = function() {
    // Resolve the record schema
    this.cdsDepositsCtrl.JSONResolver(this.schema).then(function(response) {
      that.schema = response.data;
    });

    this.findMasterFile = function() {
      return _.find(that.record._files, {'context_type': 'master'});
    };

    this.initializeStateQueue = function() {
      that.taskState = that.record._deposit.state;
      if (!_.isEmpty(that.record._deposit.state)) {
        var inter = _.intersection(depositStates, Object.keys(that.record._deposit.state));
        // Make sure that 'file_download' is not on the list
        if (inter.indexOf('file_download') === -1) {
          that.taskState.file_download = 'SUCCESS';
          that.refreshStateQueue();
        }
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
      var master = that.findMasterFile();
      if (master) {
        that.taskState.file_video_metadata_extraction = 'STARTED';
        var eventId = master.tags._event_id;
        that.getTaskFeedback(eventId, 'file_video_metadata_extraction',
          'FAILURE').then(function (data) {
          data.forEach(function (taskInfo) {
            var eventId = taskInfo.info.payload.event_id;
            var taskId = taskInfo.id;
            that.restartEvent(eventId, taskId).catch(function () {
              that.taskState.file_video_metadata_extraction = 'FAILURE';
            });
          });
        });
      }
    };

    this.restartFailedSubformats = function(subformatKeys) {
      var master = that.findMasterFile();
      var eventId = master.tags._event_id;
      that.failedSubformatKeys = _.difference(that.failedSubformatKeys,
                                              subformatKeys);
      if (!that.failedSubformatKeys.length) {
        that.taskState.file_transcode = 'STARTED';
      }
      master.subformat.forEach(
        function(subformat) {
          if (subformatKeys.includes(subformat.key)) {
            subformat.errored = false;
            subformat.progress = 0;
          }
        });
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
      depositStates.forEach(function(state) {
        that.stateReporter[state] = {
          status: state,
          message: state,
          payload: { percentage: 0 },
        };
      });
    };

    // Calculate the overall total status
    this.calculateStatus = function() {
      if (that.stateQueue.FAILURE.length) {
        return depositStatuses.FAILURE;
      } else if (that.stateQueue.STARTED.length) {
        return depositStatuses.STARTED;
      } else if (that.stateQueue.SUCCESS.length === depositStates.length) {
        // We are done - stop listening - stop sse
        return depositStatuses.SUCCESS;
      }
      return depositStatuses.PENDING;
    };

    this.videoPreviewer = function(deposit, key) {
      var videoUrl;

      var master = that.findMasterFile();
      if (master && master.subformat) {
        var finishedSubformats = master.subformat.filter(function(fmt) {
          return fmt.completed && !_.isEmpty(fmt.checksum);
        });
        if (finishedSubformats[0]) {
          videoUrl = urlBuilder.video({
            deposit: that.record._deposit.id,
            key: finishedSubformats[0].key,
          });
        }
      }
      if (videoUrl) {
        that.previewer = $sce.trustAsResourceUrl(videoUrl);
      }
    };

    this.subformatSortByKey = function(sub1, sub2) {
      if (!(sub1.key && sub2.key)) {
        return 0;
      }
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
      _.difference(keys1, keys2).forEach(function (oldSubformat) {
        subformatsNew.push({key: oldSubformat})
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
        that.record._deposit.state,
        deposit._deposit.state || {}
      );

      if (_.isEmpty(that.previewer)) {
        that.videoPreviewer();
      }
      that.lastUpdated = new Date();
    };

    // Refresh tasks from feedback endpoint
    this.fetchCurrentStatuses = function() {
      var masterFile = that.findMasterFile();
      if (masterFile) {
        var tags = masterFile.tags;
        if (tags && tags._event_id) {
          var eventId = tags._event_id;
          that.getTaskFeedback(eventId)
            .then(function(data) {
              var subformatTasks = data.filter(function(task) {
                return task.name === 'file_transcode'
              });
              // Mark all the failed subformat tasks
              subformatTasks.forEach(function(task) {
                if (task.status === 'FAILURE') {
                  task.info.payload.errored = true;
                  var key = task.info.payload.key;
                  if (!that.failedSubformatKeys.includes(key)) {
                    that.failedSubformatKeys.push(key);
                  }
                }
              });
              // Drop all finished subformats
              that.presets_finished.splice(0, that.presets_finished.length);
              // Update the state reporter with all the new info
              data.forEach(function(task) {
                that.updateStateReporter(task.name, {
                  state: task.status,
                  meta: task.info
                });
              });
              var subformatsNew = {
                subformat: subformatTasks.map(function(task) {
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

    // Update deposit based on extracted metadata from task
    this.fillMetadata = function(answer) {
      if (answer) {
        angular.merge(that.record, that.metadataToFill);
        that.makeSingleAction('SAVE_PARTIAL');
      }
      that.setOnLocalStorage('prompted', true);
      that.metadataToFill = false;
      return;
    };

    // Get metadata to automatically fill form from extracted metadata
    this.getMetadataToFill = function(metadata) {
      // Return if we have already prompted the user
      if (that.getFromLocalStorage('prompted')) {
        return false;
      }

      // Get extracted metadata
      var allMetadata = metadata || that.getFromLocalStorage('metadata');

      // No metadata extracted yet
      if (!allMetadata) {
        return false;
      }

      var metadataToFill = {};

      // Title
      var defaultTitle = that.getFromLocalStorage('basename');
      if ((that.record.title) && (that.record.title.title === defaultTitle) &&
          (allMetadata.title)) {
        metadataToFill.title = {title: allMetadata.title};
      }

      // Do not prompt user when there is no metadata to fill in
      if (_.isEmpty(metadataToFill)) {
        return false;
      }

      return metadataToFill;
    };

    // Pre-fill changes to display to the user
    this.getMetadataToDisplay = function() {
        var toDisplay = {};
        if (that.metadataToFill.title) {
            toDisplay.Name = that.metadataToFill.title.title;
        }
        return toDisplay;
    };

    // Check if extracted metadata is available for automatic form fill
    if (!this.master) {
      this.metadataToFill = that.getMetadataToFill();
    }

    // Clean storage if published
    if (this.record._deposit.status == 'published') {
      this.cleanLocalStorage();
    }

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

    this.refreshStateQueue = function() {
      var oldKeys = Object.keys(that.stateQueue);
      that.stateQueue = {};
      _.forEach(that.taskState, function(val, key) {
        that.stateQueue[val] = that.stateQueue[val] || [];
        that.stateQueue[val].push(key);
      });
      oldKeys.forEach(function(key) {
        that.stateQueue[key] = that.stateQueue[key] || [];
      });
      depositStates.forEach(function(state) {
        if (!that.taskState[state]) {
          that.stateQueue.PENDING.push(state);
        }
      });
      angular.merge(that.record._deposit.state, that.taskState);
      $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
    };

    // Initialize state the queue
    this.initializeStateQueue();
    // Initialize state reporter
    this.initializeStateReported();
    // Set stateCurrent - If null -> Waiting SSE events
    that.stateCurrent = that.stateQueue.STARTED[0] || null;
    // Check for previewer
    that.videoPreviewer();
    // Update subformat statuses
    that.fetchCurrentStatuses();
    that.fetchStatusInterval = $interval(that.fetchCurrentStatuses, 15000);
    $scope.$watch('$ctrl.taskState', that.refreshStateQueue, true);

    // Set the deposit State
    this.depositStatusCurrent = this.calculateStatus();
    // Calculate the transcode
    this.updateStateReporter = function(type, data) {
      if (type === 'file_transcode') {
        if (data.state === 'SUCCESS') {
          that.presets_finished.push(data.meta.payload.preset_quality);
          if (that.presets_finished.length === that.presets.length) {
            that.taskState.file_transcode = 'SUCCESS';
          }
          if (_.isEmpty(that.previewer)) {
            that.videoPreviewer(
              data.meta.payload.deposit_id,
              data.meta.payload.key
            );
          }
        }
        that.stateReporter[type] = angular.merge(that.stateReporter[type], {
          payload: {
            percentage: that.presets_finished.length / that.presets.length *
              100,
          },
        });
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
      // Handle my state
      $scope.$apply(function() {
        if (!(type === 'file_transcode' && data.state === 'SUCCESS') &&
            type !== 'update_deposit') {
          if (!['SUCCESS', 'FAILURE'].includes(that.taskState[type])) {
            that.taskState[type] = data.state;
          }
        }

        if (data.state === 'SUCCESS') {
          that.successCallback(type, data);
        }
      });
      // The state has been changed update the current
      that.stateCurrent = that.stateCurrentCalculate(that.stateQueue.STARTED);
      // Change the Deposit Status
      that.depositStatusCurrent = that.calculateStatus();
      // Update the metadata
      that.updateStateReporter(type, data);

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
        case 'file_video_metadata_extraction':
          var allMetadata = data.meta.payload.extracted_metadata
          that.setOnLocalStorage('metadata', allMetadata);
          that.metadataToFill = that.getMetadataToFill(allMetadata);
          break;
      }
    };

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

  // Local storage
  this.getFromLocalStorage = function(key) {
    try {
      return localStorageService.get(that.id)[key];
    } catch (error) {
      return null;
    }
  };

  this.setOnLocalStorage = function(key, value) {
    var current_info = localStorageService.get(that.id);
    current_info[key] = value;
    localStorageService.set(that.id, current_info);
  };

  this.cleanLocalStorage = function() {
    localStorageService.remove(that.id);
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
  'localStorageService'
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
