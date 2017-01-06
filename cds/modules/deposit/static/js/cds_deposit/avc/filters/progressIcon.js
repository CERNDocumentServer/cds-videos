function progressIcon() {
  return function(input) {
    switch (input) {
      case "SUCCESS":
        return "fa-check";
      case "STARTED":
        return "fa-spinner fa-spin";
      case "FAILURE":
        return "fa-times";
      case "PENDING":
        return "fa-circle";
    }
  };
}

angular.module("cdsDeposit.filters").filter("progressIcon", progressIcon);
