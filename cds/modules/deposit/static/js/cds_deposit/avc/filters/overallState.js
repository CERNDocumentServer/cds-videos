function overallState(depositStatuses) {
  return function(tasks) {
    var values = _.values(tasks);
    if (values.length !== 0) {
      if (_.contains(tasks, 'FAILURE')){
        return depositStatuses.FAILURE;
      } else if (_.contains(tasks, 'STARTED')) {
        return depositStatuses.STARTED;
      } else if (_.every(tasks, 'SUCCESS')) {
        return depositStatuses.SUCCESS;
      }
    }
    return depositStatuses.PENDING;
  };
}

overallState.$inject = ['depositStatuses'];

angular.module("cdsDeposit.filters").filter("overallState", overallState);
