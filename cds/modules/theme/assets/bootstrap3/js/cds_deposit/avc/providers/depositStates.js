import angular from "angular";

function depositStates() {
  var states = [];
  return {
    setValues: function (values) {
      states = states.concat(values);
    },
    $get: function () {
      return states;
    },
  };
}

angular.module("cdsDeposit.providers").provider("depositStates", depositStates);
