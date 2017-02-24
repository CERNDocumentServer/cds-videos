function cdsDepositsCtrl(
  $http,
  $q,
  $scope,
  $window,
  $location,
  $element,
  depositStates,
  depositSSEEvents,
  cdsAPI,
  urlBuilder
) {
  var that = this;
  this.edit = false;

  // The deposit forms
  this.depositForms = [];
  // The master deposit
  this.master = {};
  // The children deposit
  this.children = [];
  // Global loading state
  this.loading = false;
  // The connection
  this.sseListener = {};

  this.$onDestroy = function() {
    try {
      // On destroy delete the event listener
      delete $window.onbeforeunload;
      that.sseListener.close();
    } catch (error) {}
  };

  this.initState = {
    PENDING: [],
    STARTED: [],
    FAILURE: [],
    SUCCESS: [],
    REVOKED: [],
  }

  this.overallState = {};

  this.$onInit = function() {
    // Check the if the app is on top;
    var $win = angular.element($window);
    that.isOnTop = true;
    $win.on('scroll', function(e) {
      $scope.$apply(function() {
        var offset = angular.element(e.target).scrollTop();
        that.isOnTop = offset <= 0;
      });
    });

    if (this.masterLinks) {
      // Set mode to edit
      this.edit = true;
      // Fetch the project
      cdsAPI.resolveJSON(this.masterLinks.self).then(function success(
        response
      ) {
        that.addMaster(response.data);
        that.initialized = true;
        // FIXME: Remove me when the project dereferencing the videos
        angular.forEach(response.data.metadata.videos, function(video, index) {
          cdsAPI.resolveJSON(video.$reference).then(function success(response) {
            that.children.push(response.data);
          }, function error(response) {});
        });
      }, function error(response) {
        if (response.status === 403) {
          that.permissionDenied = true;
        }
      });
    }
  };

  this.addMaster = function(deposit, files) {
    if (!this.initialized) {
      if (deposit.metadata._files === undefined) {
        deposit.metadata._files = files || [];
      }
      this.master = deposit;
      // Initialized
      this.initialized = true;
      if (this.master.links.html) {
        this.handleRedirect(this.master.links.html, true);
      }
    }

    // SSE
    this.sseEventListener = function(evt) {
      // Do some magic
      var data = JSON.parse(evt.data || '{}');
      var deposit_ = 'sse.event.' + data.meta.payload.deposit_id;
      console.info('RECEIVED', evt.type, data);
      $scope.$broadcast(deposit_, evt.type, data);
    };

    // SSE stuff - move to somewhere else
    that.sseListener = new EventSource(
      urlBuilder.sse({ id: that.master.metadata._deposit.id })
    );

    that.sseListener.onerror = function(msg) {
      console.error('SSE connection error', msg);
    };

    that.sseListener.onopen = function(msg) {
      console.info('SEE connection has been opened', msg);
    };

    angular.forEach(depositSSEEvents, function(type, index) {
      that.sseListener.addEventListener(type, that.sseEventListener, false);
    });

    // Make sure we kill the connection before reload
    $window.onbeforeunload = function(event) {
      // Make sure the connection is closed after the user reloads
      try {
        that.sseListener.close();
      } catch (error) {}
    };
    // SSE
  };

  this.addChildren = function(deposit, files) {
    deposit.metadata._files = files || [];
    this.children.push(deposit);
    this.overallState[deposit.metadata._deposit.id] = angular.copy(
      that.initState
    );
  };

  this.isVideoFile = function(key) {
    var videoRegex = /(.*)\.(mp4|mov)$/;
    return key.match(videoRegex);
  };

  this.filterOutFiles = function(files) {
    // Logic to separated
    var _files = { project: [], videos: {}, videoFiles: {} };
    angular.forEach(files, function(file, index) {
      var match = that.isVideoFile(file.name);
      // Grrrrr
      file.key = file.name;
      var name;
      // If match we have a video
      if (match) {
        name = match[1];
        _files.videos[name] = file;
        _files.videoFiles[name] = [];
      } else {
        // If it's not a video then is a video related file or project
        name = file.name.split('.')[0];
        var keys = Object.keys(_files.videos);
        var _isVideoFile = false;
        angular.forEach(keys, function(key, index) {
          if (name.startsWith(key)) {
            _isVideoFile = true;
          }
        });
        if (_isVideoFile) {
          _files.videoFiles[name].push(file);
        } else {
          _files.project.push(file);
        }
      }
    });
    return _files;
  };

  this.addFiles = function(files, filesQueue) {
    // Filter files by videos and project
    var _files = this.filterOutFiles(files);
    var createMaster;

    if (!this.initialized) {
      createMaster = this.initDeposit(_files.project);
    } else {
      Array.prototype.push.apply(that.master.metadata._files, _files.project);
      createMaster = $q.resolve();
    }

    createMaster.then(function() {
      if (filesQueue) {
        Array.prototype.push.apply(filesQueue, _files.project);
      }
      var master_id = that.master.metadata._deposit.id;

      // Build the promises
      var _promises = [];
      // Find already uploaded videos
      var uploadedVideos = that.children
        .map(function(deposit) {
          if (deposit.metadata._files && deposit.metadata._files.length > 0) {
            return deposit.metadata._files[0].key;
          }
        })
        .filter(function(key) {
          return key != undefined;
        });
      _files.videos = _.reject(_files.videos, function(file) {
        return uploadedVideos.includes(file.key);
      });
      // for each files create child
      angular.forEach(
        _files.videos,
        function(file, key) {
          this.push([
            function() {
              return that.createDeposit(
                that.childrenInit,
                that.childrenSchema,
                { _project_id: master_id }
              );
            },
            function(response) {
              var _f = [];
              _f.push(file);
              _f = _f.concat(_files.videoFiles[key] || []);
              // Add default CERN copyright and year
              if (that.copyright) {
                if (!response.data.metadata.copyright) {
                  response.data.metadata.copyright = angular.merge(
                    {},
                    that.copyright,
                    {
                      year: new Date().getFullYear()
                    }
                  );
                }
              }
              that.addChildren(response.data, _f);
            },
          ]);
        },
        _promises
      );

      if (_promises.length > 0) {
        // Make requests for the videos
        that.chainedActions(_promises).then(function(data) {
          console.log('DONE chained actions', data);
        }, function(error) {
          console.log('ERROR chained actiοns', error);
        });
      }
    });
  };

  this.initDeposit = function(files) {
    var prevFiles = [];
    files = _.reject(files, function(file) {
      if (prevFiles.includes(file.key)) {
        return true;
      }
      prevFiles.push(file.key);
      return false;
    });
    return this
      .createDeposit(this.masterInit, this.masterSchema)
      .then(function(response) {
        // Create the master
        that.addMaster(response.data, files);
        // Update the master record with the references
        return cdsAPI.resolveJSON(that.master.links.self);
      })
      .then(function success(response) {
        angular.merge(that.master, response.data);
      });
  };

  this.createDeposit = function(url, schema, extra) {
    var data = angular.merge({}, { $schema: schema }, extra || {});
    return this.makeAction(url, 'POST', data);
  };

  this.makeAction = function(url, method, payload) {
    return cdsAPI.action(url, method, payload);
  };

  this.chainedActions = function(promises) {
    return cdsAPI.chainedActions(promises);
  };

  this.handleRedirect = function(url, replace) {
    if (!angular.isUndefined(url) && url !== '') {
      if (replace) {
        var path = cdsAPI.getUrlPath(url);
        $location.url(path);
        $location.replace();
      } else {
        $window.location.href = url;
      }
    }
  };

  this.JSONResolver = function(url) {
    return cdsAPI.resolveJSON(url);
  };

  // Loading Start
  $scope.$on('cds.deposit.loading.start', function(evt) {
    that.loading = true;
  });

  // Loading Stopped
  $scope.$on('cds.deposit.loading.stop', function(evt) {
    that.loading = false;
  });

  this.overallStatus = function() {
    var data = angular.copy(that.initState);
    angular.forEach(that.overallState, function(value, key) {
      angular.forEach(value, function(_i, _k) {
        data[_k] = data[_k].length + _i.length;
      });
    });
  };

  var checkStatus = function(task, status) {
    return function(child) {
      return child.metadata._deposit.state[task] == status;
    };
  };

  var getOverallState = function(children) {
    var taskStates = {};
    if (!children) {
      return;
    }
    depositStates.forEach(function(task) {
      if (children.every(checkStatus(task, 'SUCCESS'))) {
        taskStates[task] = 'SUCCESS';
      } else if (children.some(checkStatus(task, 'FAILURE'))) {
        taskStates[task] = 'FAILURE';
      } else if (children.some(checkStatus(task, 'STARTED')) ||
        children.some(checkStatus(task, 'SUCCESS'))) {
        taskStates[task] = 'STARTED';
      } else if (!children.every(checkStatus(task, undefined))) {
        taskStates[task] = 'PENDING';
      }
    });
    return taskStates;
  };

  $scope.$on('cds.deposit.status.changed', function(evt, id, state) {
    that.overallState[id] = that.overallState[id] || {};
    var thisState = that.overallState[id];
    for (var key in state) {
      thisState[key] = _.uniq((thisState[key] || []).concat(state[key]));
    }
    var statesOrder = ['PENDING', 'STARTED', 'FAILURE', 'SUCCESS'];
    statesOrder.forEach(function(curState) {
      statesOrder.some(function(prevState) {
        if (prevState == curState) {
          return true;
        }
        thisState[prevState] = _.difference(
          thisState[prevState], thisState[curState]);
      });
    });
    that.aggregatedState = getOverallState(that.children);
  });
}

cdsDepositsCtrl.$inject = [
  '$http',
  '$q',
  '$scope',
  '$window',
  '$location',
  '$element',
  'depositStates',
  'depositSSEEvents',
  'cdsAPI',
  'urlBuilder',
];

function cdsDeposits() {
  return {
    transclude: true,
    bindings: {
      // master related
      masterInit: '@',
      masterLinks: '<',
      masterSchema: '@',
      masterForm: '@',
      // children related
      childrenInit: '@',
      childrenForm: '@',
      childrenSchema: '@',
      // general template base
      formTemplatesBase: '@?',
      formTemplates: '=?',
      // Dropbox related
      dropboxAppKey: '@',
      // Default cern copyright
      copyright: '=?',
    },
    controller: cdsDepositsCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    },
  };
}

angular.module('cdsDeposit.components').component('cdsDeposits', cdsDeposits());
