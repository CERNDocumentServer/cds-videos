import angular from "angular";
import _ from "lodash";

function overallState(depositStatuses) {
  return function (tasks) {
    var values = _.values(_.omit(tasks, "file_video_extract_chapter_frames"));
    if (values.length !== 0) {
      if (_.includes(values, "FAILURE")) {
        return depositStatuses.FAILURE;
      } else if (_.includes(values, "STARTED")) {
        return depositStatuses.STARTED;
      } else if (
        _.every(values, function (val) {
          return val === "SUCCESS";
        })
      ) {
        return depositStatuses.SUCCESS;
      }
    }
    return depositStatuses.PENDING;
  };
}

overallState.$inject = ["depositStatuses"];

angular.module("cdsDeposit.filters").filter("overallState", overallState);
