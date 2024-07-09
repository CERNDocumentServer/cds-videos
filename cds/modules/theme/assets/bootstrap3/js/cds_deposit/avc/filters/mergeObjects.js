import angular from "angular";

function mergeObjects($filter) {
  // Filter to allow merging of two objects inside angular expressions
  return function (dst, src) {
    return angular.merge({}, dst, src);
  };
}
mergeObjects.$inject = ["$filter"];

angular.module("cdsDeposit.filters").filter("mergeObjects", mergeObjects);
