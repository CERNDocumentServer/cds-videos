import angular from "angular";

function depositExtractedMetadata() {
  var metadata = {};
  return {
    setValues: function (values) {
      metadata = values;
    },
    $get: function () {
      return metadata;
    },
  };
}

angular
  .module("cdsDeposit.providers")
  .provider("depositExtractedMetadata", depositExtractedMetadata);
