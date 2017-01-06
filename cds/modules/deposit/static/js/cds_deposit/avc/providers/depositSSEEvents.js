function depositSSEEvents() {
  var states = [];
  return {
    setValues: function(values) {
      states = states.concat(values);
    },
    $get: function() {
      return states;
    }
  };
}

angular.module('cdsDeposit.providers')
  .provider('depositSSEEvents', depositSSEEvents);
