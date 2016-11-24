function cdsDepositCtrl($scope, $q) {
  var that = this;

  this.statuses = {
    PUBLISHED: 0,
    ERROR: 1,
    LOADING: 2,
    UPLOADING: 3,
    EVENTS: 4,
    IDLE: 5,
  };

  this.states = {
    file_upload: 0
  };

  this.progress_ = function() {
    return this.progress;
  }

  this.currentStatus = this.statuses.IDLE;
  this.currentState = null;

  this.progress = 0;
  // The Upload Queue
  this.filesQueue = [];

  // The deposit can have the follwoing states
  this.$onInit = function() {
    // Resolve the record schema
    this.cdsDepositsCtrl.JSONResolver(this.schema)
    .then(function(response) {
      that.schema = response.data;
    });
    this.alerts = {};
    $scope.$on(
      'cds.deposit.alert.' + this.record._deposit.id,
      function(evt, type, msg) {
        console.error('Alert', type, msg);
        that.alerts[type] = msg;
      }
    );

    // Register related events from sse
    var depositListenerName = 'sse.event.' + this.record._deposit.id;
    $scope.$on(
      depositListenerName,
      function(evt, type, data) {
        console.log('RECEIVE DEPOSIT', type, data);
        if (data.state === 'FAILURE') {
          $scope.$broadcast(
            'cds.deposit.alert.' + that.record._deposit.id,
            'danger',
            data.meta.message
          );
        }
        if (data.meta.payload.key) {
          $scope.$broadcast(
            depositListenerName + '.' + data.meta.payload.key,
            type,
            data
          );
        }
    });

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
            $scope.$broadcast('cds.deposit.validation.error', value);
          });
        });
        deferred.resolve();
      }
    };
  }

  this.guessEndpoint = function(endpoint) {
    if (Object.keys(that.links).indexOf(endpoint) > -1) {
      return that.links[endpoint];
    }
    return endpoint;
  };

  this.cleanData = function(data, unwanted) {
    var _unwantend = unwanted || [[null], [undefined]];
    // Delete the _files before request
    delete data._files;
    angular.forEach(data, function(value, key) {
      angular.forEach(_unwantend, function(_value) {
        if (angular.equals(_value, value))  {
          delete data[key];
        }
      });
    });
    return data;
  }

  // Do a single action at once
  this.makeSingleAction = function(endpoint, method, redirect) {
    // Guess the endpoint
    var url = this.guessEndpoint(endpoint);
    return this.cdsDepositsCtrl
    .makeAction(url, method, that.cleanData(that.record));
  }

  // Do multiple actions at once
  this.makeMultipleActions = function(actions, redirect) {
    var promises = [];
    var cleanRecord = that.cleanData(that.record);
    angular.forEach(actions, function(action, index) {
      var url = that.guessEndpoint(action[0]);
      this.push(function() {
        return that.cdsDepositsCtrl.makeAction(url, action[1], cleanRecord);
      });
    }, promises);
    return that.cdsDepositsCtrl.chainedActions(promises);
  }

  this.onSuccessAction = function(response) {
    // Post success process
    that.postSuccessProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.success', response);
    // Make the form pristine again
    that.depositFormModel.$setPristine();
  }

  this.onErrorAction = function(response) {
    // Post error process
    that.postErrorProcess(response);
    // Inform the parents
    $scope.$emit('cds.deposit.error', response);
  }
}

cdsDepositCtrl.$inject = ['$scope', '$q'];

function cdsDeposit() {
  return {
    transclude: true,
    bindings: {
      index: '=',
      master: '@',
      // Interface related
      updateRecordAfterSuccess: '@',
      // Deposit related
      schema: '@',
      record: '=',
      links: '=',
      // The form model
      depositFormModel: '=?',
    },
    require: {
      cdsDepositsCtrl: '^cdsDeposits'
    },
    controller: cdsDepositCtrl,
    template: "<div ng-transclude></div>"
  };
}

angular.module('cdsDeposit.components')
  .component('cdsDeposit', cdsDeposit());
