function cdsActionsCtrl($scope, cdsAPI) {
  var that = this;
  this.$onInit = function () {

    this.actionHandler = function (actions, redirect) {
      that.cdsDepositCtrl.preActions();
      var method = _.isArray(actions) ? 'makeMultipleActions' : 'makeSingleAction';
      return that.cdsDepositCtrl[method](actions)
        .then(
          that.cdsDepositCtrl.onSuccessAction,
          that.cdsDepositCtrl.onErrorAction
        )
        .finally(that.cdsDepositCtrl.postActions);
    };

    this.deleteDeposit = function () {
      that.actionHandler('DELETE').then(function () {
        var children = that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata.videos;
        for (var i in children) {
          if (children[i]._deposit.id === that.cdsDepositCtrl.id) {
            children.splice(i, 1);
          }
        }
        delete that.cdsDepositCtrl.cdsDepositsCtrl.overallState[that.cdsDepositCtrl.id];
      });
    };

    this.saveAllPartial = function () {
      var depositsCtrl = that.cdsDepositCtrl.cdsDepositsCtrl,
        master = depositsCtrl.master,
        project = master.metadata,
        videos = project.videos;

      if (that.cdsDepositCtrl.master) {
        var actionName = 'SAVE_PARTIAL',
          videoActions = getVideoActions(depositsCtrl, actionName, videos),
          projectAction = getProjectAction(depositsCtrl, actionName, master, project);

        videoActions.push(projectAction);

        that.cdsDepositCtrl.preActions();
        cdsAPI.chainedActions(videoActions)
          .then(function success(responseList) {
            notifyUpdateCompleted(responseList);
          }, function error(errorList) {
            notifyUpdateCompleted(errorList);
          })
          .finally(that.cdsDepositCtrl.postActions);
      }

      function getVideoActions(depositsCtrl, actionName, videos) {
        return videos
            .filter(function (video) {
              return video._deposit.status === 'draft';
            })
            .map(function (video) {
              return cdsAPI.cleanData(video);
            })
            .map(function (cleanedVideo) {
              var depositType = 'video',
                url = depositsCtrl.helpers.guessEndpoint(cleanedVideo, depositType, actionName, cleanedVideo.links);

              return function () {
                return depositsCtrl.helpers.makeAction(
                  url,
                  depositType,
                  actionName,
                  cleanedVideo
                );
              };
            });
      }

      function getProjectAction(depositsCtrl, actionName, master, project) {
        var cleanedProject = cdsAPI.cleanData(project),
          depositType = 'project',
          url = depositsCtrl.helpers.guessEndpoint(cleanedProject, depositType, actionName, master.links);

          return function () {
            return depositsCtrl.helpers.makeAction(
              url,
              depositType,
              actionName,
              cleanedProject
            );
          };
      }

      function notifyUpdateCompleted(responseList) {
        responseList.forEach(function (response) {
            depositsCtrl.broadcastEvent('cds.deposit.project.updated', {
                'depositId': response.data.metadata._deposit.id,
                'response': response
              });
          });
      }
    };
  };
}

cdsActionsCtrl.$inject = ['$scope', 'cdsAPI'];

function cdsActions() {
  return {
    bindings: {},
    require: {cdsDepositCtrl: '^cdsDeposit'},
    controller: cdsActionsCtrl,
    templateUrl: function ($element, $attrs) {
      return $attrs.template;
    }
  };
}

angular.module('cdsDeposit.components').component('cdsActions', cdsActions());
