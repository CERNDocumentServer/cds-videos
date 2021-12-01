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

  // Action loading
  that.actionLoading = false;

  this.framesReady = false;

  // Deposit type
  that.depositType = that.master ? 'project' : 'video';

  // Deposit status
  this.isPublished = function() {
    return that.record._deposit.status === 'published';
  };

  // used in the Admin panel to restart tasks
  this.allFlowsTasksByName = {}

  this.cachedFlowTasksById = {};

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
  // Initialize currentStartedTaskName
  this.currentStartedTaskName = null;

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

    function findFilesByContextType(recordFiles, type) {
      return _.find(recordFiles, {'context_type': type});
    }

    this.findMasterFile = function() {
      return findFilesByContextType(that.record._files, 'master');
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
          if (propPath === 'keywords') {
            $scope.$broadcast('cds.deposit.form.keywords.inherit', record);
          }
        } else if (ownElement instanceof Array &&
            ownElement.every(hasNoProperties)) {
          var inheritedArray = angular.copy(inheritedVal);
          accessElement(record, propPath, inheritedArray);
        }
      });

      // Set form dirty
      that.setDirty();
    };

    this.getTaskFeedback = function(flowId) {
      var url = urlBuilder.taskFeedback({ flowId: flowId });
      return cdsAPI.action(url, 'GET', {}, jwt).then(function(data) {
        return _.flatten(data.data, true);
      }).catch(function(e) {
        return _.flatten(e.data, true);
      });
    };

    this.triggerRestartFlow = function() {
      var masterFile = that.findMasterFile();
      var flowId = _.get(masterFile, 'tags.flow_id', undefined);
      $scope.$broadcast('cds.deposit.workflow.restart', flowId);
    }

    this.triggerRestartFlowTask = function(flowId, taskId) {
      that.restartFlowTask(flowId, taskId)
        .then(function() {
          // Fetch feedback to update the Interface
          that.fetchFlowTasksStatuses();
        })
    }

    this.restartFlowTask = function(flowId, taskId) {
      var url = urlBuilder.restartTask({ taskId: taskId, flowId: flowId });
      return cdsAPI.action(url, 'PUT');
    };

    this.initializeStateReported = function() {
      that.stateReporter = {};
      that.presets = [];
      depositStates.forEach(function(state) {
        that.stateReporter[state] = {
          status: 'PENDING',
          message: state,
        };
      });
      _.forEach(that.record._cds.state, function(value, state) {
        that.stateReporter[state].status = value;
      });
      that.calculateCurrentDepositStatus();
    };

    this.videoPreviewer = function() {
      var master = that.findMasterFile();
      if (master && master.subformat) {
        var finishedSubformats = master.subformat.filter(function(fmt) {
          return fmt.completed && !_.isEmpty(fmt.checksum);
        });
        if (finishedSubformats.length > 0) {
          var videoUrl = urlBuilder.video({
            deposit: that.record._deposit.id,
            key: finishedSubformats[0].key,
          });
          that.previewer = $sce.trustAsResourceUrl(videoUrl);
        }
      }
    };

    // update deposit files only because metadata might have been changed in the form
    // but not yet saved
    this.updateDeposit = function(deposit) {
      // sort subformat by key to display them nicely
      deposit._files[0]?.subformat?.sort(
        // take advantage of JS: parseInt("1080p") -> 1080
        (a, b) => parseInt(a.key) < parseInt(b.key)
      );
      that.record._files = angular.copy(deposit._files);
      that.currentMasterFile = that.findMasterFile();
      that.record._cds.state = angular.copy(
        deposit._cds.state || {}
      );

      if (_.isEmpty(that.previewer)) {
        that.videoPreviewer();
      }
    };


    this.refetchRecordOnTaskStatusChanged = function (flowTasksById) {
      // init if not set yet
      var cachedFlowTasksById = _.isEmpty(that.cachedFlowTasksById) ? angular.copy(flowTasksById) : that.cachedFlowTasksById;

      var reFetchRecord = false;
      for (var taskId in flowTasksById) {
        var cachedTask = _.get(cachedFlowTasksById, taskId, null);
        if (!cachedTask) {
          // something wrong with the cached tasks, maybe a flow restart?
          // refetch the record to be sure
          reFetchRecord = true;
          break;
        }

        var statusHasChanged = flowTasksById[taskId]["status"] !== cachedTask["status"];
        if (statusHasChanged) {
          reFetchRecord = true;
          break;
        }
      }

      // update cache
      that.cachedFlowTasksById = angular.copy(flowTasksById);

      if (reFetchRecord) {
        that.cdsDepositsCtrl.fetchRecord();
      }
    };


    this.updateSubformatsTranscodingStatus = function(flowTasks) {
      // Updates master file subformats field, needed for files tab
      var transcodingTasks = _.groupBy(flowTasks, "name")["file_transcode"];
      var subformatsNew = transcodingTasks.filter(function(task) {
        return task.info;
      }).map(function(task) {
        // inject `status_completed`
        var payload = task.info.payload;
        if (task.status === 'SUCCESS') {
          payload.status_completed = true;
        } else if (task.status === 'FAILURE') {
          payload.status_failure = true;
        } else if (task.status === 'PENDING') {
          payload.status_pending = true;
        } else if (task.status === 'STARTED') {
          payload.status_started = true;
        } else if (task.status === 'CANCELLED') {
          payload.status_cancelled = true;
        }
        return payload;
      });

      that.currentMasterFile = that.findMasterFile();
      that.currentMasterFile.subformat = subformatsNew;
    }

    // Refresh tasks from feedback endpoint
    this.fetchFlowTasksStatuses = function() {
      if (that.isDraft() ){
        var masterFile = that.findMasterFile();
        var flowId = _.get(masterFile, 'tags.flow_id', undefined);
        if (flowId) {
          that.getTaskFeedback(flowId)
            .then(function(data) {
              var tasksById = _.groupBy(data, 'id');
              that.allFlowsTasksByName = _.groupBy(data, 'name');
              // each taskId is an array: '1233': [task]
              // remove the array for each key to make it simple to use
              for (var key in tasksById) {
                tasksById[key] = tasksById[key][0]
              }
              // Update task states in record
              that.refetchRecordOnTaskStatusChanged(tasksById);

              that.updateSubformatsTranscodingStatus(data);

              // Update the state reporter with all the new info
              data.forEach(function(task) {
                that.updateStateReporter(task["name"], task["info"], task["status"]);
              });
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
    this.updateStateReporter = function(name, info, status) {
      if (status && !info.status) {
        info.status = status;
      }
      if (that.stateReporter[name].status !== info.status) {
        // Get metadata
        $scope.$broadcast('cds.deposit.task', name, info.status, info);
      }
      that.stateReporter[name] = angular.copy(info);
    };

    this.calculateCurrentDepositStatus = function() {
      // The state has been changed update the current
      var currentStartedTaskName = null;
      for (var task of depositStates) {
        var state = that.record._cds.state[task];
        if (state === 'STARTED') {
          currentStartedTaskName = task;
          break;
        }
      }
      that.currentStartedTaskName = currentStartedTaskName;

      // Change the Deposit Status
      var values = _.values(that.record._cds.state);
      if (!values.length) {
        that.currentDepositStatus = null;
      } else if (values.includes(depositStatuses.FAILURE)) {
        that.currentDepositStatus = depositStatuses.FAILURE;
      } else if (values.includes(depositStatuses.STARTED)) {
        that.currentDepositStatus = depositStatuses.STARTED;
      } else if (values.includes(depositStatuses.PENDING)) {
        that.currentDepositStatus = depositStatuses.PENDING;
      } else {
        that.currentDepositStatus = depositStatuses.SUCCESS;
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

    // cdsDeposit flows

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
    // Set currentStartedTaskName
    that.currentStartedTaskName = null;
    // Initialize state reporter
    this.initializeStateReported();
    // Check for previewer
    that.videoPreviewer();
    // Update subformat statuses
    that.fetchFlowTasksStatuses();
    that.fetchStatusInterval = $interval(that.fetchFlowTasksStatuses, 5000);
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
      return that.currentDepositStatus === that.depositStatuses.FAILURE;
    };

    this.displayPending = function() {
      return that.currentDepositStatus === that.depositStatuses.PENDING;
    };

    this.displayStarted = function() {
      return that.currentDepositStatus === that.depositStatuses.STARTED;
    };

    this.displaySuccess = function() {
      return that.currentDepositStatus === that.depositStatuses.SUCCESS &&
        !that.isPublished() &&
        !that.record.recid;
    };

    this.postSuccessProcess = function(responses) {
      // Get only the latest response (in case of multiple actions)
      var response = (responses[responses.length - 1] || responses).data;
      // Update record: use _ and not ng because otherwise it will destroy references to the parent record
      that.record = _.merge(that.record, response.metadata);
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
      that.calculateCurrentDepositStatus();
    }
    if (newVal['file_video_extract_frames'] === 'SUCCESS') {
      that.framesReady = true;
    } else {
      that.framesReady = false;
    }
  }, true);

  // Listen for any updates
  $scope.$on('cds.deposit.metadata.update.' + that.id, function(evt, data) {
    that.updateDeposit(data);
    // after having fetched the record, we need to immediately fetch the statuses because
    // otherwise CANCELLED subformats disappears for a few seconds given that they are
    // not part of the `_files[0].subformats` just fetched
    that.fetchFlowTasksStatuses();
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
