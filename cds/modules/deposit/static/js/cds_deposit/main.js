$(document).ready(function() {
  // show warning if IE (not supported for deposit)
  var $cdsDepositIeWarning = $('#cds-deposit-ie-warning');
  if ($cdsDepositIeWarning.length && isIEBelowEdge()) {
    $cdsDepositIeWarning.removeClass('hidden');
  }

  function isIEBelowEdge() {
    return (
      navigator.appName == 'Microsoft Internet Explorer' ||
      !!(navigator.userAgent.match(/Trident/) ||
      navigator.userAgent.match(/rv:11/)) ||
      (typeof $.browser !== "undefined" && $.browser.msie == 1)
    );
  }
});
