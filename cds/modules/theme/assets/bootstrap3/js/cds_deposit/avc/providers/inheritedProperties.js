import angular from "angular";

function inheritedProperties() {
  var properties = [];
  return {
    setValues: function (values) {
      properties = values;
    },
    $get: function () {
      return properties;
    },
  };
}

angular
  .module("cdsDeposit.providers")
  .provider("inheritedProperties", inheritedProperties);
