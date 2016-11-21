function cdsActionsCtrl($scope) {
  var that = this;
  this.$onInit = function() {
    this.postActions = function() {
      // Stop loading
      $scope.$emit('cds.deposit.loading.stop');
      that.cdsDepositCtrl.loading = false;
    }
    this.actionHandler = function(type, method) {
      // Start loading
      $scope.$emit('cds.deposit.loading.start');
      that.cdsDepositCtrl.loading = true;
      that.cdsDepositCtrl.makeSingleAction(type, method)
      .then(
        that.cdsDepositCtrl.onSuccessAction,
        that.cdsDepositCtrl.onErrorAction
      ).finally(that.postActions);
    }
    this.actionMultipleHandler = function(actions) {
      // Start loading
      $scope.$emit('cds.deposit.loading.start');
      that.cdsDepositCtrl.loading = true;
      that.cdsDepositCtrl.makeMultipleActions(actions)
      .then(
        that.cdsDepositCtrl.onSuccessAction,
        that.cdsDepositCtrl.onErrorAction
      ).finally(that.postActions);
    }
  }
}

cdsActionsCtrl.$inject = ['$scope'];

function cdsActions() {
  return {
    bindings: {
    },
    require: {
      cdsDepositCtrl: '^cdsDeposit'
    },
    controller: cdsActionsCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    }
  }
}

angular.module('cdsDeposit.components')
  .component('cdsActions', cdsActions());
