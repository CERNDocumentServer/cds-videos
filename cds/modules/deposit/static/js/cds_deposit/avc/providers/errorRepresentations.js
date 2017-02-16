function errorRepresentations() {
  var representations = {};
  return {
    setValues: function(values) {
      representations = values;
    },
    $get: function() {
      return representations;
    }
  };
}

angular.module('cdsDeposit.providers')
  .provider('errorRepresentations', errorRepresentations);
