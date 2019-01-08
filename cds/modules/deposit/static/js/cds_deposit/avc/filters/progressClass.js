function progressClass() {
  return function(input) {
    switch (input) {
      case "SUCCESS":
      case "DEPOSIT_STATE/SUCCESS":
        return "text-success";
      case "STARTED":
      case "DEPOSIT_STATE/STARTED":
        return "text-warning";
      case "FAILURE":
      case "DEPOSIT_STATE/FAILURE":
        return "text-danger";
      case "PENDING":
      case "DEPOSIT_STATE/PENDING":
        return "text-muted";
    }
  };
}

angular.module("cdsDeposit.filters").filter("progressClass", progressClass);
