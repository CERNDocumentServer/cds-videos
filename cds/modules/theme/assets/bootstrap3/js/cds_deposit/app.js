// Main deps
import angular from "angular";
import $ from "jquery";

// avc module
import "./avc/avc.module";

// avc filters
import "./avc/filters/mergeObjects.js";
import "./avc/filters/orderTasks.js";
import "./avc/filters/overallState.js";
import "./avc/filters/progressClass.js";
import "./avc/filters/progressIcon.js";
import "./avc/filters/toInt.js";
import "./avc/filters/parseAutocomplete.js";

// avc providers
import "./avc/providers/depositExtractedMetadata.js";
import "./avc/providers/depositStates.js";
import "./avc/providers/depositStatuses.js";
import "./avc/providers/depositActions.js";
import "./avc/providers/inheritedProperties.js";
import "./avc/providers/taskRepresentations.js";
import "./avc/providers/stateReducer.js";
import "./avc/providers/typeReducer.js";
import "./avc/providers/urlBuilder.js";

// avc factories
import "./avc/factories/states";

// avc components
import "./avc/components/cdsActions.js";
import "./avc/components/cdsDeposit.js";
import "./avc/components/cdsDeposits.js";
import "./avc/components/cdsForm.js";
import "./avc/components/cdsUploader.js";
import "./avc/components/cdsRemoteUploader.js";
import "./avc/components/cdsVideoList.js";

$(document).ready(function () {
  // show warning if IE (not supported for deposit)
  var $cdsDepositIeWarning = $("#cds-deposit-ie-warning");
  if ($cdsDepositIeWarning.length && isIEBelowEdge()) {
    $cdsDepositIeWarning.removeClass("hidden");
  }

  function isIEBelowEdge() {
    return (
      navigator.appName == "Microsoft Internet Explorer" ||
      !!(
        navigator.userAgent.match(/Trident/) ||
        navigator.userAgent.match(/rv:11/)
      ) ||
      (typeof $.browser !== "undefined" && $.browser.msie == 1)
    );
  }

  $(".dropdown-toggle").dropdown();
});

angular.element(document).ready(function () {
  angular.bootstrap(
    document.getElementById("cds-deposit"),
    ["cds", "cdsDeposit", "ngModal", "ngSanitize"],
    { strictDi: true }
  );
});
