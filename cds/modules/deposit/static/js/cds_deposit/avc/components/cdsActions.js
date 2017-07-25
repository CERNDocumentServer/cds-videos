function cdsActionsCtrl($scope) {
  var that = this;
  this.$onInit = function() {

    this.actionHandler = function(actions, redirect) {
      that.cdsDepositCtrl.preActions();
      var method = _.isArray(actions) ? 'makeMultipleActions' : 'makeSingleAction';
      return that.cdsDepositCtrl[method](actions)
        .then(
          that.cdsDepositCtrl.onSuccessAction,
          that.cdsDepositCtrl.onErrorAction
        )
        .finally(that.cdsDepositCtrl.postActions);
    };

    this.deleteDeposit = function() {
      that.actionHandler('DELETE').then(function() {
        var children = that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata.videos;
        for (var i in children) {
          if (children[i]._deposit.id == that.cdsDepositCtrl.id) {
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
