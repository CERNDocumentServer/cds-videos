function progressIcon() {
  return function(input) {
    switch (input) {
      case "SUCCESS":
      case "DEPOSIT_STATE/SUCCESS":
        return "fa-check";
      case "STARTED":
      case "DEPOSIT_STATE/STARTED":
        return "fa-spinner fa-spin";
      case "FAILURE":
      case "DEPOSIT_STATE/FAILURE":
        return "fa-times";
      case "PENDING":
      case "DEPOSIT_STATE/PENDING":
        return "fa-spinner fa-spin";
    }
  };
}

angular.module("cdsDeposit.filters").filter("progressIcon", progressIcon);
