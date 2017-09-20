function parseAutocomplete() {
  return function(input, key) {
    console.log('PARSE', input)
    if (typeof(input) === "object") {
      return _.get(input, key || 'name');
    }
    return input;
  };
}

angular.module('cdsDeposit.filters').filter('parseAutocomplete', parseAutocomplete);
