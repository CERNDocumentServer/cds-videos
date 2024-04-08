import angular from "angular";

function orderTasks(depositStates) {
  return function (input) {
    var ordered = new Map();
    if (input) {
      depositStates.forEach(function (task) {
        if (input.hasOwnProperty(task)) {
          ordered[task] = input[task];
        }
      });
    }
    return ordered;
  };
}

angular.module("cdsDeposit.filters").filter("orderTasks", orderTasks);
