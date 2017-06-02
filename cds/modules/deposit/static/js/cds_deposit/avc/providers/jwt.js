function jwt() {
  var header = {};

  function setHeader(header_) {
    header = header_;
  }

  return {
    setHeader: function(header_) {
      setHeader(header_);
    },
    $get: function() {
      return header;
    }
  };
}

angular.module('cdsDeposit.providers')
  .provider('jwt', jwt);
