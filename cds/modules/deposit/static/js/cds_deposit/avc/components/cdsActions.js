function cdsActionsCtrl($scope, cdsAPI) {
  var that = this;
  this.$onInit = function () {

    this.actionHandler = function (actions, redirect) {
      that.cdsDepositCtrl.preActions();
      var method = _.isArray(actions) ? 'makeMultipleActions' : 'makeSingleAction';
      return that.cdsDepositCtrl[method](actions)
        .then(
          function(response) {
            var _check = method === 'makeMultipleActions' ? actions : [actions];
            var message;
            if (_check.indexOf('DELETE') > -1) {
              message = 'Succefully deleted.'
            } else if (_check.indexOf('PUBLISH') > -1) {
              message = 'Succefully published.'
            }
            that.cdsDepositCtrl.onSuccessAction(response, message);
          },
          that.cdsDepositCtrl.onErrorAction
        )
        .finally(that.cdsDepositCtrl.postActions);
    };

    this.deleteDeposit = function () {
      that.actionHandler('DELETE').then(
        function () {
          var children = that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata.videos;
          for (var i in children) {
            if (children[i]._deposit.id === that.cdsDepositCtrl.id) {
              children.splice(i, 1);
            }
          }
          delete that.cdsDepositCtrl.cdsDepositsCtrl.overallState[that.cdsDepositCtrl.id];
        }
      );
    };

    this.saveAllPartial = function () {
      var depositsCtrl = that.cdsDepositCtrl.cdsDepositsCtrl,
        master = depositsCtrl.master,
        project = master.metadata,
        videos = project.videos;

      if (that.cdsDepositCtrl.master) {
        var actionName = 'SAVE_PARTIAL',
          videoActions = getVideoActions(actionName, videos),
          projectAction = getProjectAction(actionName, master, project);

        videoActions.push(projectAction);

        that.cdsDepositCtrl.preActions();
        cdsAPI.chainedActions(videoActions)
          .then(
            that.cdsDepositCtrl.onSuccessActionMultiple,
            that.cdsDepositCtrl.onErrorAction
          )
          .finally(that.cdsDepositCtrl.postActions);
      }

      function getVideoActions(actionName, videos) {
        return videos
            .filter(function (video) {
              return video._deposit.status === 'draft';
            })
            .map(function (video) {
              return cdsAPI.cleanData(video);
            })
            .map(function (cleanedVideo) {
              var depositType = 'video',
                url = cdsAPI.guessEndpoint(cleanedVideo, depositType, actionName, cleanedVideo.links);

              return function () {
                return cdsAPI.makeAction(
                  url,
                  depositType,
                  actionName,
                  cleanedVideo
                );
              };
            });
      }

      function getProjectAction(actionName, master, project) {
        var cleanedProject = cdsAPI.cleanData(project),
          depositType = 'project',
          url = cdsAPI.guessEndpoint(cleanedProject, depositType, actionName, master.links);

          return function () {
            return cdsAPI.makeAction(
              url,
              depositType,
              actionName,
              cleanedProject
            );
          };
      }
    };
  };

  $scope.$on('cds.deposit.project.saveAll', function(evt) {
    that.saveAllPartial();
  });

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
