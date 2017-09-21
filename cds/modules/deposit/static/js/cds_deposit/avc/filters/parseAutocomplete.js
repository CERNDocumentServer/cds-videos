function parseAutocomplete() {
  return function(input, key) {
    if (typeof(input) === "object") {
      return _.get(input, key || 'name');
    }
    return input;
  };
}

angular.module('cdsDeposit.filters').filter('parseAutocomplete', parseAutocomplete);
