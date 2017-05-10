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

  // Failed subformats list
  that.failedSubformatKeys = [];

  // Deposit type
  Object.defineProperty(this, 'depositType', {
    get: function() {
      return that.master ? 'project' : 'video';
    }
  })

  // Deposit status
  this.isPublished = function() {
    return that.record._deposit.status === 'published';
  };

  this.isDraft = function() {
    return that.record._deposit.status === 'draft';
  };

  this.hasCategory = function() {
    return !that.record.category;
  }

  // Initilize stateCurrent
  this.stateCurrent = null;

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

    this.inheritMetadata = function(specific) {
      // Inherit metadata from project
      var record = that.record;
      var master = that.cdsDepositsCtrl.master.metadata;
      var paths = (specific !== undefined ) ? specific : inheritedProperties;
      angular.forEach(paths, function(propPath) {
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
      // Set form dirty
      that.setDirty();
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
        var eventId = master.tags._event_id;
        that.getTaskFeedback(eventId, 'file_video_metadata_extraction',
          'FAILURE').then(function (data) {
          data.forEach(function (taskInfo) {
            var eventId = taskInfo.info.payload.event_id;
            var taskId = taskInfo.id;
            that.restartEvent(eventId, taskId);
          });
        });
      }
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
      _.forEach(that.record._deposit.state, function(value, state) {
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
        if (that.presets.length == 0) {
          var eventId = masterFile.tags._event_id;
          if (eventId) {
            var eventUrl = urlBuilder.eventInfo({eventId: eventId});
            var updatePresets = function (resp) {
              that.presets = angular.copy(resp.data.presets);
            };
            fetchPresetsPromise = cdsAPI.action(eventUrl, 'GET')
              .then(updatePresets, updatePresets);
          }
        }
        fetchPresetsPromise.then(function() {
          that.stateReporter['file_transcode'] = angular.merge(
            that.stateReporter['file_transcode'], {
              payload: {
                percentage: subformatsFinished / that.presets.length * 100,
              },
            });
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
              var groupedTasks = _.groupBy(data, 'name');
              var transcodeTasks = groupedTasks.file_transcode;
              // Update the state reporter with all the new info
              data.forEach(function(task) {
                that.updateStateReporter(task.name, task.info, task.status);
              });
              // Update subformat info
              var subformatsNew =  transcodeTasks.filter(function(task) {
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
          if (that.stateReporter[type].status != data.status) {
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
        var state = that.record._deposit.state[task];
        if ((state == 'STARTED' || state == 'PENDING') && !stateCurrent) {
          stateCurrent = task;
        }
      });
      that.stateCurrent = stateCurrent;
      // Change the Deposit Status
      var values = _.values(that.record._deposit.state);
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
      $scope.$emit('cds.deposit.status.changed', that.id, that.record._deposit.state);
    };

    this.currentMasterFile = this.findMasterFile();
    // Initialize state reporter
    this.initializeStateReported();
    // Set stateCurrent - If null -> Waiting SSE events
    that.stateCurrent = null;
    // Check for previewer
    that.videoPreviewer();
    // Update subformat statuses
    that.fetchCurrentStatuses();
    that.fetchStatusInterval = $interval(that.fetchCurrentStatuses, 10000);
    $scope.$watch('$ctrl.record._deposit.state', that.refreshStateQueue, true);

    // Listen for task status changes
    $scope.$on('cds.deposit.task', function(evt, type, status, data) {
      if (type == 'file_video_metadata_extraction' && status == 'SUCCESS') {
        var allMetadata = data.payload.extracted_metadata
        that.setOnLocalStorage('metadata', allMetadata);
        that.metadataToFill = that.getMetadataToFill(allMetadata);
      }
    });
    // Register related events from sse
    var depositListenerName = 'sse.event.' + this.id;
    this.sseEventListener = $scope.$on(depositListenerName, function(
      evt,
      type,
      data
    ) {
      // Handle my state
      $scope.$apply(function() {
        if (type === 'update_deposit') {
          that.updateDeposit(data.meta.payload.deposit);
        } else if (type == 'file_video_metadata_extraction' ||
                   type == 'file_video_extract_frames') {
          that.updateStateReporter(type, data.meta, data.state);
        } else if (type == 'file_transcode') {
          var masterFile = that.findMasterFile();
          if (masterFile) {
            var subformats = masterFile.subformat;
            if (!subformats) {
              masterFile.subformat = [];
              subformats = masterFile.subformat;
            }
            var curSubformat = _.find(subformats, {key: data.meta.payload.key});
            if (curSubformat) {
              curSubformat = angular.merge(curSubformat, data.meta.payload);
            } else {
              curSubformat = angular.copy(data.meta.payload);
              subformats.push(curSubformat);
            }

            if (curSubformat.percentage === 100 && data.state === 'SUCCESS') {
              curSubformat.completed = true;
            } else if (data.state === 'FAILURE') {
              curSubformat.errored = true;
            }

            that.processSubformats();
          }
          that.updateStateReporter(type, data.meta, data.state);
        }
      });
      // Update deposit current state
      that.calculateCurrentState();
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
    if (that.links && Object.keys(that.links).indexOf(link) > -1) {
      return that.links[link];
    } else {
      if (!that.master) {
        // If the link is self just return the self video url
        if (link === 'self') {
          return urlBuilder.selfVideo({
            deposit: that.record._deposit.id,
          })
        } else if (link == 'bucket') {
          return urlBuilder.bucketVideo({
            bucket: that.record._buckets.deposit,
          })
        }
        // If the link is different return the action video url
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

  this.setDirty = function() {
    _.invoke(that.depositFormModels, '$setDirty');
  }

  this.setPristine = function() {
    _.invoke(that.depositFormModels, '$setPristine');
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
      links: '=?',
    },
    require: { cdsDepositsCtrl: '^cdsDeposits' },
    controller: cdsDepositCtrl,
    template: '<div ng-transclude></div>',
  };
}

angular.module('cdsDeposit.components').component('cdsDeposit', cdsDeposit());
