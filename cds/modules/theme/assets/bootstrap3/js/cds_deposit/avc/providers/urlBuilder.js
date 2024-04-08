import angular from "angular";
import _ from "lodash";

function urlBuilder() {
  var blueprints = {};

  function setBlueprint(key, value) {
    // underscorejs templates
    blueprints[key] = _.template(value);
  }
  return {
    setBlueprints: function (blueprints_) {
      angular.forEach(blueprints_, function (value, key) {
        setBlueprint(key, value);
      });
    },
    $get: function () {
      return blueprints;
    },
  };
}

angular.module("cdsDeposit.providers").provider("urlBuilder", urlBuilder);
