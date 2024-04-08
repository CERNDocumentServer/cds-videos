import angular from "angular";

function mergeObjects() {
  // Filter to allow merging of two objects inside angular expressions
  return function (dst, src) {
    return angular.merge({}, dst, src);
  };
}

angular.module("cdsDeposit.filters").filter("mergeObjects", mergeObjects);
