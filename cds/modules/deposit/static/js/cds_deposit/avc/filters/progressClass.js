function progressClass() {
  return function(input) {
    switch (input) {
      case "SUCCESS":
        return "text-success";
      case "STARTED":
        return "text-warning";
      case "FAILURE":
        return "text-danger";
      case "PENDING":
      case "CANCELLED":
        return "text-muted";
    }
  };
}

angular.module("cdsDeposit.filters").filter("progressClass", progressClass);
