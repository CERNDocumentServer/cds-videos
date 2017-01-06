function toInt() {
  return function(input) {
    var result;
    try {
        result = parseInt(input);
    } catch(error) {
      result = input;
    }
    return result;
  };
}

angular.module('cdsDeposit.filters')
  .filter('toInt', toInt);
