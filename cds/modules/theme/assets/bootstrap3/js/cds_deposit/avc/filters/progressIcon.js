import angular from "angular";

function progressIcon() {
  return function (input) {
    switch (input) {
      case "SUCCESS":
        return "fa-check";
      case "PENDING":
      case "STARTED":
        return "fa-spinner fa-spin";
      case "FAILURE":
        return "fa-times";
      case "PENDING":
        return "fa-spinner fa-spin";
      default:
        return "";
    }
  };
}

angular.module("cdsDeposit.filters").filter("progressIcon", progressIcon);
