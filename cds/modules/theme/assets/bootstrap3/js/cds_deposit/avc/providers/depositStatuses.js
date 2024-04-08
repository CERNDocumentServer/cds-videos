import angular from "angular";

function depositStatuses() {
  var statuses = {};
  return {
    setValues: function (values) {
      statuses = values;
    },
    $get: function () {
      return statuses;
    },
  };
}

angular
  .module("cdsDeposit.providers")
  .provider("depositStatuses", depositStatuses);
