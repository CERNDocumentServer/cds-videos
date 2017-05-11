function cdsActionsCtrl($scope) {
  var that = this;
  this.$onInit = function() {
    this.postActions = function() {
      // Stop loading
      $scope.$emit('cds.deposit.loading.stop');
      that.cdsDepositCtrl.loading = false;
    };

    this.actionHandler = function(action) {
      // Start loading
      $scope.$emit('cds.deposit.loading.start');
      that.cdsDepositCtrl.loading = true;
      return that.cdsDepositCtrl
        .makeSingleAction(action)
        .then(
          that.cdsDepositCtrl.onSuccessAction,
          that.cdsDepositCtrl.onErrorAction
        )
        .finally(that.postActions);
    };

    this.actionMultipleHandler = function(actions) {
      // Start loading
      $scope.$emit('cds.deposit.loading.start');
      that.cdsDepositCtrl.loading = true;
      return that.cdsDepositCtrl
        .makeMultipleActions(actions)
        .then(
          that.cdsDepositCtrl.onSuccessAction,
          that.cdsDepositCtrl.onErrorAction
        )
        .finally(that.postActions);
    };

    this.deleteDeposit = function() {
      that.actionHandler('DELETE').then(function() {
        var children = that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata.videos;
        for (var i in children) {
          if (children[i].metadata._deposit.id == that.cdsDepositCtrl.id) {
            children.splice(i, 1);
          }
        }
        delete that.cdsDepositCtrl.cdsDepositsCtrl.overallState[that.cdsDepositCtrl.id];
      });
    };
  };
}

cdsActionsCtrl.$inject = [ '$scope' ];

function cdsActions() {
  return {
    bindings: {},
    require: { cdsDepositCtrl: '^cdsDeposit' },
    controller: cdsActionsCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    },
  };
}

angular.module('cdsDeposit.components').component('cdsActions', cdsActions());
