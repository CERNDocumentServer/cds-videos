function cdsDepositCtrl(
  $scope,
  $q,
  $timeout,
  $sce,
  depositStates,
  depositStatuses,
  cdsAPI,
  urlBuilder,
  typeReducer
) {
  var that = this;
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

  // FIXME Init stateQueue -  maybe ```Object(depositStatuses).keys()```
  this.stateQueue = { PENDING: [], STARTED: [], FAILURE: [], SUCCESS: [] };

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

  // The deposit can have the follwoing depositStates
  this.$onInit = function() {
    // Resolve the record schema
    this.cdsDepositsCtrl.JSONResolver(this.schema).then(function(response) {
      that.schema = response.data;
    });

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
        var videoFile = that.record._files[0];
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
    };

    this.initializeStateReported = function() {
      that.stateReporter = {};
      that.presets_finished = [];
      // FIXME: Get them from the Webhooks
      that.presets = [ '360p', '720p', '480p', '240p', '1080p', '1024p' ];
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
      if (that.stateQueue.SUCCESS.indexOf('file_download') > -1 || key) {
        that.previewer = $sce.trustAsResourceUrl(
          urlBuilder.video({
            deposit: deposit || that.record._deposit.id,
            key: key || that.record._files[0].key,
          })
        );
      }
    };

    this.updateDeposit = function(deposit) {
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

    // cdsDeposit events

    // Success message
    // Loading message
    // Error message

    // Messages Success
    $scope.$on('cds.deposit.success', function(evt, response) {
      if (evt.currentScope == evt.targetScope) {
        that.alerts = [];
        that.alerts.push({
          message: response.status || 'Success',
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
          if (that.presets_finished.length === 1) {
            that.videoPreviewer(
              that.record._deposit.id,
              that.record._files[0].key
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
          that.stateCurrent = that.stateQueue.STARTED[0] || null;
          // Change the Deposit Status
          that.depositStatusCurrent = that.calculateStatus();
          $scope.$emit('cds.deposit.status.changed', that.id, that.stateQueue);
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

    this.failureCallback = function(type, data) {};

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

  this.guessEndpoint = function(endpoint) {
    if (Object.keys(that.links).indexOf(endpoint) > -1) {
      return that.links[endpoint];
    }
    return endpoint;
  };

  this.dismissAlert = function(alert) {
    this.alerts.splice(_.indexOf(this.alerts, alert.alert), 1);
  };

  // Do a single action at once
  this.makeSingleAction = function(endpoint, method, redirect) {
    // Guess the endpoint
    var url = this.guessEndpoint(endpoint);
    return this.cdsDepositsCtrl.makeAction(
      url,
      method,
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
        var url = that.guessEndpoint(action[0]);
        this.push(function() {
          return that.cdsDepositsCtrl.makeAction(url, action[1], cleanRecord);
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
    that.depositFormModel.$setPristine();
  };

  this.onErrorAction = function(response) {
    // Post error process
    that.postErrorProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.error', response);
  };
}

cdsDepositCtrl.$inject = [
  '$scope',
  '$q',
  '$timeout',
  '$sce',
  'depositStates',
  'depositStatuses',
  'cdsAPI',
  'urlBuilder',
  'typeReducer',
];

/**
 * @ngdoc component
 * @name cdsDeposit
 * @description
 *   Hendles the actions and SSE events for each ``deposit_id``. For each
 *   ``children`` a new ``cds-deposit`` directive will be generated.
 * @attr {String} index - The deposit index in the list of deposits.
 * @attr {Boolean} master - If this deposit is the ``master``.
 * @attr {Boolean} updateRecordAfterSuccess - Update the record after action.
 * @attr {Integer} updateRecordInBackground - Update the record in background.
 * @attr {String} schema - The URI for the deposit type schema.
 * @attr {Object} links - The deposit action links (i.e. ``self``).
 * @attr {Object} record - The record metadata.
 * @attr {Object} depositFormModel - The angular-schema-form model to be used.
 * @example
 *  Example:
 *  <cds-deposit
 *   master="true"
 *   links="$ctrl.master.links"
 *   update-record-after-success="true"
 *   schema="{{ $ctrl.masterSchema }}"
 *   record="$ctrl.master.metadata"
 *   deposit-form-model="$ctrl.depositForms[0]"
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
      // The form model
      depositFormModel: '=?',
    },
    require: { cdsDepositsCtrl: '^cdsDeposits' },
    controller: cdsDepositCtrl,
    template: '<div ng-transclude></div>',
  };
}

angular.module('cdsDeposit.components').component('cdsDeposit', cdsDeposit());
