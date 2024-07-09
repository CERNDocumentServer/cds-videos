import angular from "angular";
import _ from "lodash";

function cdsActionsCtrl($scope, $q, cdsAPI) {
  var that = this;

  this.$onInit = function () {
    this.actionHandler = function (userActions) {
      var hasMultipleActions = _.isArray(userActions),
        method = hasMultipleActions
          ? "makeMultipleActions"
          : "makeSingleAction";

      that.cdsDepositCtrl.preActions();
      return chainExtraActions(userActions).then(function (response) {
        return that.cdsDepositCtrl[method](userActions)
          .then(function (response) {
            var _check = hasMultipleActions ? userActions : [userActions],
              message;
            if (_check.indexOf("DELETE") > -1) {
              message = "Successfully deleted.";
            } else if (_check.indexOf("PUBLISH") > -1) {
              message = "Successfully published.";
            }
            that.cdsDepositCtrl.onSuccessAction(response, message);
          }, that.cdsDepositCtrl.onErrorAction)
          .finally(that.cdsDepositCtrl.postActions);
      });
    };

    this.deleteVideo = function () {
      that.actionHandler("DELETE").then(function () {
        var children =
          that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata.videos;
        for (var i in children) {
          if (children[i]._deposit.id === that.cdsDepositCtrl.id) {
            children.splice(i, 1);
          }
        }
      });
    };

    $scope.$on("cds.deposit.delete", function () {
      that.deleteVideo();
    });

    /*
     * Show a warning message if user wants to edit a published video but the project is already published
     */
    this.showCannotEditVideoDialog = false;
    this.editPublished = function () {
      if (
        that.cdsDepositCtrl.depositType === "video" &&
        that.cdsDepositCtrl.isProjectPublished()
      ) {
        that.showCannotEditVideoDialog = true;
      } else {
        that.actionHandler(["EDIT", "SAVE_PARTIAL"]);
        that.cdsDepositCtrl.changeShowAll(false);
      }
    };

    this.saveAllPartial = function () {
      if (that.cdsDepositCtrl.depositType === "project") {
        var saveActions = getSaveAllMakeActions();
        that.cdsDepositCtrl.preActions();
        return cdsAPI
          .chainedActions(saveActions)
          .then(
            that.cdsDepositCtrl.onSuccessActionMultiple,
            that.cdsDepositCtrl.onErrorAction
          )
          .finally(that.cdsDepositCtrl.postActions);
      }
    };

    /*
     * Save videos first, then save project: this is because the save project
     * response will contain also the videos metadata, which must be up-to-date.
     */
    $scope.$on("cds.deposit.project.saveAll", function () {
      that.saveAllPartial();
    });

    /*
     * If user is publishing a project, save videos and project first
     */
    function chainExtraActions(actions) {
      var arrayActions = _.isArray(actions) ? actions : [actions],
        isPublishing = arrayActions.indexOf("PUBLISH") > -1,
        extraActionPromises;

      if (isPublishing && that.cdsDepositCtrl.depositType === "project") {
        extraActionPromises = cdsAPI.chainedActions(getSaveAllMakeActions());
      } else {
        // empty promise
        extraActionPromises = $q.when();
      }
      return extraActionPromises;
    }

    /*
     * Return actions to save videos and project
     */
    function getSaveAllMakeActions() {
      var depositsCtrl = that.cdsDepositCtrl.cdsDepositsCtrl,
        master = depositsCtrl.master,
        project = master.metadata,
        videos = project.videos,
        actionName = "SAVE_PARTIAL",
        videoActions = getVideoMakeActions(actionName, videos),
        projectAction = getProjectMakeAction(actionName, master, project);

      videoActions.push(projectAction);

      return videoActions;
    }

    function getVideoMakeActions(actionName, videos) {
      return videos
        .filter(function (video) {
          return video._deposit.status === "draft";
        })
        .map(function (video) {
          return function () {
            var depositType = "video",
              cleanedVideo = cdsAPI.cleanData(video);
            var url = cdsAPI.guessEndpoint(
              cleanedVideo,
              depositType,
              actionName,
              cleanedVideo.links
            );

            return cdsAPI.makeAction(
              url,
              depositType,
              actionName,
              cleanedVideo
            );
          };
        });
    }

    function getProjectMakeAction(actionName, master, project) {
      return function () {
        var depositType = "project",
          cleanedProject = cdsAPI.cleanData(project),
          url = cdsAPI.guessEndpoint(
            cleanedProject,
            depositType,
            actionName,
            master.links
          );

        return cdsAPI.makeAction(url, depositType, actionName, cleanedProject);
      };
    }
  };
}

cdsActionsCtrl.$inject = ["$scope", "$q", "cdsAPI"];

function cdsActions() {
  return {
    bindings: {},
    require: { cdsDepositCtrl: "^cdsDeposit" },
    controller: cdsActionsCtrl,
    templateUrl: function (element, attrs) {
      return attrs.template;
    },
  };
}

angular.module("cdsDeposit.components").component("cdsActions", cdsActions());
