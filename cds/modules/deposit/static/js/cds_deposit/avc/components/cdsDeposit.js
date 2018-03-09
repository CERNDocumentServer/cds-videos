function cdsDepositCtrl(
  $scope,
  $window,
  $q,
  $timeout,
  $interval,
  $sce,
  depositExtractedMetadata,
  depositStates,
  depositStatuses,
  inheritedProperties,
  cdsAPI,
  urlBuilder,
  typeReducer,
  localStorageService,
  jwt,
  toaster
) {

  var that = this;

  this.depositFormModels = [];

  // The Upload Queue
  this.filesQueue = [];

  // Checkout
  this.lastUpdated = new Date();

  // Add depositExtractedMetadata to the scope
  this.depositExtractedMetadata = depositExtractedMetadata;

  // Add depositStatuses to the scope
  this.depositStatuses = depositStatuses;

  // Alerts
  this.alerts = [];

  // Metadata information to automatically fill form
  this.metadataToFill = false;

  // Ignore server validation errors for the following fields
  this.noValidateFields = ['description'];

  this.previewer = null;

  // Failed subformats list
  that.failedSubformatKeys = [];

  // Action loading
  that.actionLoading = false;

  this.framesReady = false;

  // Deposit type
  that.depositType = that.master ? 'project' : 'video';

  // Deposit status
  this.isPublished = function() {
    return that.record._deposit.status === 'published';
  };

  // Webhooks available tasks
  this.webhookAvailableEventTasks = {};

  // Webhooks event_id
  this.webhookEventId = null;

  this.isProjectPublished = function() {
    var isPublished;
    if (that.depositType === 'project') {
      isPublished = that.isPublished();
    } else {
      var master = that.cdsDepositsCtrl.master.metadata;
      isPublished = master._deposit.status === 'published';
    }
    return isPublished;
  }

  this.isDraft = function() {
    return that.record._deposit.status === 'draft';
  };

  this.hasCategory = function() {
    return !that.record.category;
  }

  this.initShowAll = function (){
    that.showAll = !that.isPublished();
  }

  this.changeShowAll = function(hide) {
    that.showAll = (hide) ? false : true;
  }
  // Initilize stateCurrent
  this.stateCurrent = null;

  this.$onDestroy = function() {
    try {
      // Destroy listener
      $interval.cancel(that.fetchStatusInterval);
    } catch (error) {}
  };

  this.$postLink = function() {
    // Set pristine the form
    $timeout(function () {
      that.setPristine();
    }, 1500);
  }

  // The deposit can have the following depositStates
  this.$onInit = function() {
    // Init showAll
    this.initShowAll();

    // Loading
    this.loading = false;

    this.findFilesByContextType = function(type) {
      return _.find(that.record._files, {'context_type': type});
    }

    this.findMasterFile = function() {
      return this.findFilesByContextType('master');
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
    }

    var hasNoProperties = function(obj) {
      return Object.getOwnPropertyNames(obj).length == 0;
    };

    this.inheritMetadata = function(specific, forceInherit) {
      // Inherit metadata from project
      var record = that.record;
      var master = that.cdsDepositsCtrl.master.metadata;
      var paths = (specific !== undefined ) ? specific : inheritedProperties;
      angular.forEach(paths, function(propPath) {
        var inheritedVal = accessElement(master, propPath);
        var ownElement = accessElement(record, propPath);
        if ((inheritedVal && !ownElement) || (inheritedVal && forceInherit === true)) {
          accessElement(record, propPath, inheritedVal);
        } else if (ownElement instanceof Array &&
            ownElement.every(hasNoProperties)) {
          var inheritedArray = angular.copy(inheritedVal);
          accessElement(record, propPath, inheritedArray);
        }
      });

      $scope.$broadcast('cds.deposit.form.keywords.inherit', record);
      // Set form dirty
      that.setDirty();
    };

    this.getTaskFeedback = function(eventId, taskName, taskStatus) {
      var url = urlBuilder.taskFeedback({ eventId: eventId });
      return cdsAPI.action(url, 'GET', {}, jwt).then(function(data) {
        data = _.flatten(data.data, true);
        if (taskName || taskStatus) {
          return data.filter(function (taskInfo) {
            return (!taskName || taskInfo.name === taskName) &&
              (!taskStatus || taskInfo.status === taskStatus);
          });
        } else {
          return data;
        }
      });
    };

    this.triggerRestartAllEvents = function() {
      // Trigger restart workflow
      $scope.$broadcast('cds.deposit.workflow.restart');
    }

    this.triggerRestartEvent = function(eventId, taskId) {
      that.restartEvent(eventId, taskId)
        .then(function() {
          // Fetch feedback to update the Interface
          that.fetchCurrentStatuses();
        })
    }

    this.restartEvent = function(eventId, taskId) {
      var url = urlBuilder.restartEvent({ taskId: taskId, eventId: eventId });
      return cdsAPI.action(url, 'PUT');
    };

    this.restartFailedSubformats = function(subformatKeys) {
      var master = that.findMasterFile();
      var eventId = master.tags._event_id;
      master.subformat.forEach(
        function(subformat) {
          if (subformatKeys.includes(subformat.key)) {
            subformat.errored = false;
            subformat.percentage = 0;
          }
        });
      that.processSubformats();
      that.getTaskFeedback(eventId, 'file_transcode', 'FAILURE')
        .then(function(data) {
          var restartEvents = data.filter(function(taskInfo) {
            return subformatKeys.includes(taskInfo.info.payload.key);
          }).map(function(taskInfo) {
            var eventId = taskInfo.info.payload.event_id;
            var taskId = taskInfo.id;
            return that.restartEvent(eventId, taskId);
          });
          $q.all(restartEvents).then(function() {
            that.fetchCurrentStatuses();
          });
      });
    };

    this.initializeStateReported = function() {
      that.stateReporter = {};
      that.presets = [];
      depositStates.forEach(function(state) {
        that.stateReporter[state] = {
          status: 'PENDING',
          message: state,
          payload: { percentage: 0 },
        };
      });
      _.forEach(that.record._cds.state, function(value, state) {
        that.stateReporter[state].status = value;
      });
      that.calculateCurrentState();
    };

    that.processSubformats = function() {
      var masterFile = that.findMasterFile();
      if (masterFile && masterFile.subformat) {
        var subformats = masterFile.subformat;
        // Sort by key length and key
        subformats = _.chain(subformats).filter(function(subformat) {
            return subformat.hasOwnProperty('key');
          }).sortBy('key').sortBy(function(subformat) {
            return subformat.key.length;
          }).value();
        masterFile.subformat = subformats;

        // Update failed subformat list
        that.failedSubformatKeys = subformats.filter(function(subformat) {
          return subformat.errored;
        }).map(function(subformat) {
          return subformat.key;
        });

        var subformatsFinished = subformats.filter(
          function(subformat) {
            return subformat.completed;
          }).length;

        var fetchPresetsPromise = $q.resolve();
        if (that.presets && that.presets.length == 0) {
          var eventId = masterFile.tags._event_id;
          if (eventId) {
            var eventUrl = urlBuilder.eventInfo({eventId: eventId});
            var updatePresets = function (resp) {
              that.presets = angular.copy(resp.data.presets);
            };
            fetchPresetsPromise = cdsAPI.action(eventUrl, 'GET', {}, jwt)
              .then(updatePresets, updatePresets);
          }
        }
        fetchPresetsPromise.then(function() {
          if (that.presets && that.presets.length > 0) {
            that.stateReporter['file_transcode'] = angular.merge(
              that.stateReporter['file_transcode'], {
                payload: {
                  percentage: subformatsFinished / that.presets.length * 100,
                },
              });
          }
        });
      }
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

    this.updateDeposit = function(deposit) {
      that.record._files = angular.merge(
        [],
        that.record._files,
        deposit._files || []
      );
      that.processSubformats();
      that.currentMasterFile = that.findMasterFile();

      // Check for new state
      that.record._cds.state = angular.merge(
        that.record._cds.state,
        deposit._cds.state || {}
      );

      if (_.isEmpty(that.previewer)) {
        that.videoPreviewer();
      }
      that.lastUpdated = new Date();
    };

    // Refresh tasks from feedback endpoint
    this.fetchCurrentStatuses = function() {
      // Update only if it is ``draft``
      if (that.isDraft()){
        var masterFile = that.findMasterFile();
        var eventId = _.get(masterFile, 'tags._event_id', undefined);
        that.webhookEventId = eventId;
        if (eventId) {
          that.getTaskFeedback(eventId)
            .then(function(data) {
              var groupedTasks = _.groupBy(data, 'name');
              // Update the available task events
              that.webhookAvailableEventTasks = groupedTasks;
              var transcodeTasks = groupedTasks.file_transcode;
              // Update the state reporter with all the new info
              data.forEach(function(task) {
                that.updateStateReporter(task.name, task.info, task.status);
              });
              // Update subformat info
              if (!transcodeTasks) {
                return;
              }
              var subformatsNew = transcodeTasks.filter(function(task) {
                return task.info;
              }).map(function(task) {
                var payload = task.info.payload;
                if (payload.percentage === 100 && task.status === 'SUCCESS') {
                  payload.completed = true;
                } else if (task.status === 'FAILURE') {
                  payload.errored = true;
                }
                return payload;
              });
              masterFile.subformat = subformatsNew;
              that.processSubformats();
              that.calculateCurrentState();
            });
        }
      }
    };

    // Update deposit based on extracted metadata from task
    this.fillMetadata = function(answer) {
      var metadataToFill = that.metadataToFill[0];
      var metadataToFill_values = that.metadataToFill[1];
      if (answer) {
        // Merge the data
        angular.merge(that.record, metadataToFill);
        that.preActions();
        // Make a partial Save
        that.makeSingleAction('SAVE_PARTIAL')
          .then(
            that.onSuccessAction,
            that.onErrorAction
          )
          .finally(that.postActions);
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

      // Metadata extracted
      var metadataToFill = {};
      var metadataToFill_values = {};
      Object.keys(depositExtractedMetadata.values).forEach(function(item, index){
        value = depositExtractedMetadata.values[item](metadataToFill, allMetadata);
        if(value){
          metadataToFill_values[item] = value;
        }
      });

      // Do not prompt user when there is no metadata to fill in
      if (_.isEmpty(metadataToFill)) {
        return false;
      }

      return [metadataToFill, metadataToFill_values];
    };

    // Pre-fill changes to display to the user
    this.getMetadataToDisplay = function() {
        if(that.metadataToFill){
          return that.metadataToFill[1];
        }
        return {}
    };

    // Calculate the transcode
    this.updateStateReporter = function(type, data, status) {
      if (data) {
        if (status && !data.status) {
          data.status = status;
        }
        if (type === 'file_transcode') {
          if (!_.isEmpty(data.status) && data.status === 'SUCCESS' && _.isEmpty(that.previewer)) {
            that.videoPreviewer(
              data.payload.deposit_id,
              data.payload.key
            );
          }
        } else {
          if (that.stateReporter[type].status !== data.status) {
            $scope.$broadcast('cds.deposit.task', type, data.status, data);
          }
          that.stateReporter[type] = angular.copy(data);
        }
      }
    };

    this.calculateCurrentState = function() {
      // The state has been changed update the current
      var stateCurrent = null;
      depositStates.forEach(function(task) {
        var state = that.record._cds.state[task];
        if ((state === 'STARTED' || state === 'PENDING') && !stateCurrent) {
          stateCurrent = task;
        }
      });
      that.stateCurrent = stateCurrent;
      // Change the Deposit Status
      var values = _.values(that.record._cds.state);
      if (!values.length) {
        that.depositStatusCurrent = null;
      } else if (values.includes('FAILURE')) {
        that.depositStatusCurrent = depositStatuses.FAILURE;
      } else if (values.includes('STARTED')) {
        that.depositStatusCurrent = depositStatuses.STARTED;
      } else if (!values.includes('PENDING')) {
        that.depositStatusCurrent = depositStatuses.SUCCESS;
      } else {
        that.depositStatusCurrent = depositStatuses.STARTED;
      }
    };

    // Check if extracted metadata is available for automatic form fill
    if (!this.master) {
      this.metadataToFill = that.getMetadataToFill();
    }

    // Clean storage if published
    if (this.isPublished()) {
      this.cleanLocalStorage();
    }

    // cdsDeposit events

    // Success message
    // Loading message
    // Error message

    // Messages Success
    $scope.$on('cds.deposit.success', function(evt, message) {
      if (evt.currentScope === evt.targetScope) {
        that.alerts = [];
        that.alerts.push({
          message: 'Success!',
          type: 'success'
        });
        // Push a notification only if a custom message exists
        if (message !== undefined) {
          toaster.pop({
            type: 'success',
            title: that.record.title ? that.record.title.title : 'Video',
            body: message,
            bodyOutputType: 'trustedHtml'
          });
        }
      }
    });
    // Messages Error
    $scope.$on('cds.deposit.error', function(evt, response) {
      if (evt.currentScope === evt.targetScope) {
        that.alerts = [];
        that.alerts.push({
          message: response.data.message,
          type: 'danger',
          errors: response.data.errors || []
        });
        var message = (String(response.status || '').startsWith('5')) ?
          'Internal Sever Error' : response.data.message;
        // Push a notification
        toaster.pop({
          type: 'error',
          title: that.record.title ? that.record.title.title : 'Video',
          body: message,
          bodyOutputType: 'trustedHtml'
        });
      }
    });

    this.currentMasterFile = this.findMasterFile();
    // Initialize state reporter
    this.initializeStateReported();
    // Set stateCurrent
    that.stateCurrent = null;
    // Check for previewer
    that.videoPreviewer();
    // Update subformat statuses
    that.fetchCurrentStatuses();
    that.fetchStatusInterval = $interval(that.fetchCurrentStatuses, 15000);
    // What the order of contributors and check make it dirty, throttle the
    // function for 1sec
    $scope.$watch(
      '$ctrl.record.contributors',
      _.throttle(that.setDirty, 1000),
      true
    );
    $scope.$watch('$ctrl.record._deposit.status', function() {
      if (CKEDITOR) {
        $timeout(function() {
          Object.values(CKEDITOR.instances).forEach(function (instance) {
            try {
                instance.setReadOnly(instance.element.$.disabled);
            } catch(error) {
                // Do nothing probably not initialized yet
            }
          });
        }, 0);
      }
    });

    // Listen for task status changes
    $scope.$on('cds.deposit.task', function(evt, type, status, data) {
      if (type == 'file_video_metadata_extraction' && status == 'SUCCESS') {
        var allMetadata = data.payload.extracted_metadata
        that.setOnLocalStorage('metadata', allMetadata);
        that.metadataToFill = that.getMetadataToFill(allMetadata);
      } else if (type == 'file_video_extract_frames' && status == 'SUCCESS') {
        that.framesReady = true;
      }
    });

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
      return that.depositStatusCurrent === that.depositStatuses.SUCCESS &&
        !that.isPublished() &&
        !that.record.recid;
    };

    this.postSuccessProcess = function(responses) {
      // Get only the latest response (in case of multiple actions)
      var response = (responses[responses.length - 1] || responses).data;
      // Update record: use _ and not ng because otherwise it will destroy references to the parent record
      that.record = _.merge(that.record, response.metadata);
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

  this.dismissAlert = function(alert) {
    this.alerts.splice(_.indexOf(this.alerts, alert.alert), 1);
  };

  // Do a single action at once
  this.makeSingleAction = function(action) {
    var cleanRecord = cdsAPI.cleanData(that.record),
      url = cdsAPI.guessEndpoint(cleanRecord, that.depositType, action, that.links);

    return cdsAPI.makeAction(
      url,
      that.depositType,
      action,
      cleanRecord
    );
  };

  // Do multiple actions at once
  this.makeMultipleActions = function(actions) {
    var promises = [];
    var cleanRecord = cdsAPI.cleanData(that.record);
    angular.forEach(
      actions,
      function(action, index) {
        var url = cdsAPI.guessEndpoint(cleanRecord, that.depositType, action, that.links);

        this.push(function() {
          return cdsAPI.makeAction(
            url,
            that.depositType,
            action,
            cleanRecord
          );
        });
      },
      promises
    );
    return cdsAPI.chainedActions(promises);
  };

  this.preActions = function() {
    // Stop loading
    $scope.$emit('cds.deposit.loading.start');
    that.loading = true;
    that.actionLoading = true;
  };

  this.postActions = function() {
    // Stop loading
    $scope.$emit('cds.deposit.loading.stop');
    that.loading = false;
    that.actionLoading = false;
  };

  this.onSuccessActionMultiple = function(response, message) {
    // Emit an event for all deposits
    $scope.$broadcast('cds.deposit.pristine.all');
    // Go through the normal proccess
    that.onSuccessAction(response, message);
  };

  this.onSuccessAction = function(response, message) {
    // Post success process
    that.postSuccessProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.success', message);
    // Make the form pristine again
    that.setPristine();
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

  this.setDirty = function() {
    _.each(that.depositFormModels, function(model) {
        model.$setDirty();
    });
  }

  this.setPristine = function() {
    _.each(that.depositFormModels, function(model) {
        model.$setPristine();
    });
  }

  // Local storage
  this.getFromLocalStorage = function(key) {
    try {
      return _.get(localStorageService.get(that.id), key, undefined);
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
  };

  $scope.$on('cds.deposit.pristine.all', function(evt) {
    // Set that to pristine
    that.setPristine();
  });

  // Listen for any changes in the record state
  $scope.$watch('$ctrl.record._cds.state', function(newVal, oldVal, scope) {
    if (!_.isEqual(newVal, oldVal)){
      // The states have been changed
      that.calculateCurrentState();
    }
    if (newVal['file_video_extract_frames'] === 'SUCCESS') {
      that.framesReady = true;
    } else {
      that.framesReady = false;
    }
  }, true);
  // Listen for any updates
  $scope.$on('cds.deposit.metadata.update.' + that.id, function(evt, data) {
    // Update only if it's draft
    if (that.isDraft()) {
      that.updateDeposit(data);
    }
  });

  $window.onbeforeunload = function() {
    // Warn the user if there are any unsaved changes
    if (!that.cdsDepositsCtrl.onExit && !that.isPristine()) {
      that.cdsDepositsCtrl.onExit = true;
      return 'Unsaved changes have been detected.';
    }
  }
}

cdsDepositCtrl.$inject = [
  '$scope',
  '$window',
  '$q',
  '$timeout',
  '$interval',
  '$sce',
  'depositExtractedMetadata',
  'depositStates',
  'depositStatuses',
  'inheritedProperties',
  'cdsAPI',
  'urlBuilder',
  'typeReducer',
  'localStorageService',
  'jwt',
  'toaster'
];

/**
 * @ngdoc component
 * @name cdsDeposit
 * @description
 *   Handles the actions for each ``deposit_id``. For each
 *   ``children`` a new ``cds-deposit`` directive will be generated.
 * @attr {String} index - The deposit index in the list of deposits.
 * @attr {Boolean} master - If this deposit is the ``master``.
 * @attr {Integer} updateRecordInBackground - Update the record in background.
 * @attr {String} schema - The URI for the deposit type schema.
 * @attr {Object} links - The deposit action links (i.e. ``self``).
 * @attr {Object} record - The record metadata.
 * @example
 *  Example:
 *  <cds-deposit
 *   master="true"
 *   links="$ctrl.master.links"
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
      updateRecordInBackground: '@?',
      // Deposit related
      id: '=',
      schema: '=',
      record: '=',
      links: '=?',
    },
    require: { cdsDepositsCtrl: '^cdsDeposits' },
    controller: cdsDepositCtrl,
    template: '<div ng-transclude></div>',
  };
}

angular.module('cdsDeposit.components').component('cdsDeposit', cdsDeposit());
