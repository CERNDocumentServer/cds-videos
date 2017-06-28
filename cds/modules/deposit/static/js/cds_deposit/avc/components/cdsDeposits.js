function cdsDepositsCtrl(
  $http,
  $q,
  $scope,
  $window,
  $location,
  $element,
  depositStates,
  depositActions,
  depositSSEEvents,
  cdsAPI,
  urlBuilder,
  localStorageService
) {
  var that = this;
  this.edit = false;

  // The master deposit
  this.master = {};
  // Global loading state
  this.loading = false;
  // The connection
  this.sseListener = {};
  // The access rights
  this.accessRights = {};
  // The last video upload promise
  this.lastVideoUpload = $q.resolve();

  // Schemas and forms
  that.masterSchemaResolved = {};
  that.childrenSchemaResolved = {};
  that.childrenFormResolved = {};
  that.masterFormResolved = {};

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

    cdsAPI.resolveJSON(this.masterSchema).then(function(response) {
      that.masterSchemaResolved = response.data;
    });
    cdsAPI.resolveJSON(this.childrenSchema).then(function(response) {
      that.childrenSchemaResolved = response.data;
    });
    cdsAPI.resolveJSON(this.childrenForm).then(function(response) {
      that.childrenFormResolved = response.data;
    });
    cdsAPI.resolveJSON(this.masterForm).then(function(response) {
      that.masterFormResolved = response.data;
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
      }, function error(response) {
        if (response.status === 403) {
          that.permissionDenied = true;
        }
      });
    }

    that.categoriesPromise = $http.get(urlBuilder.categories()).then(
      function(data) {
        return data.data.hits.hits;
      });
  };

  this.addMaster = function(deposit, files) {
    if (!this.initialized) {
      if (_.isEmpty(deposit.metadata._files)) {
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
    this.master.metadata.videos.push(deposit.metadata);
    this.overallState[deposit.metadata._deposit.id] = angular.copy(
      that.initState
    );
  };

  this.isVideoFile = function(key) {
    var videoExtensions = (that.videoExtensions || 'mp4,mkv,mov').split(',');
    var fileKey = null;
    videoExtensions.forEach(function(ext) {
      if (key.toLowerCase().endsWith('.' + ext.toLowerCase())) {
        fileKey = that.extractBasename(key);
      }
    });
    return fileKey;
  };

  this.extractBasename = function(key) {
    return key.slice(0, key.lastIndexOf('.'));
  }

  this.filterOutFiles = function(files) {
    // Separate videos from other files
    var [videos, other] = _.partition(files, function(f) {
      return that.isVideoFile(f.name);
    });

    // Index videos by their key
    var videos = _.keyBy(videos, function(video) {
      return that.isVideoFile(video.name);
    });
    angular.forEach(videos, function(video) {
      if (!video.key) {
        video.key = video.name;
      }
    });
    var videoKeys = _.keys(videos);
    var _files = {
      project: [],
      videos: videos,
      videoFiles: _.map(videos, _.constant([]))
    };

    angular.forEach(other, function(file, index) {
      file.key = file.name;
      var basename = that.extractBasename(file.name);

      // Check if file is related to a video (i.e. same basename)
      var videoMatch = _.find(videoKeys, function(videoKey) {
        return basename.startsWith(videoKey);
      });

      var toPush = (videoMatch) ? _files.videoFiles[basename] : _files.project
      toPush.push(file);
    });

    return _files;
  };

  this.addFiles = function(files, filesQueue) {
    // Do nothing if files array is empty
    if (!files) {
      return;
    }
    // Filter files by videos and project
    var _files = this.filterOutFiles(files);
    var createMaster;

    if (!this.initialized) {
      createMaster = this.initProject(_files.project);
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
      var uploadedVideos = that.master.metadata.videos
        .map(function(deposit) {
          if (deposit._files && deposit._files.length > 0) {
            return deposit._files[0].key;
          }
        })
        .filter(function(key) {
          return key != undefined;
        });
      var videoKeys = _.keys(_files.videos).map(function (name) {
        return _files.videos[name].key;
      });
      that.duplicateVideos = _.intersection(videoKeys, uploadedVideos);
      _files.videos = _.omit(_files.videos, function (val) {
        return that.duplicateVideos.includes(val.key)
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
                'video',
                {
                  _project_id: master_id,
                  title: { title: key }
                }
              );
            },
            function(response) {
              // Map from deposit IDs to video basenames (local storage)
              videoId = response.data.metadata._deposit.id
              localStorageService.set(videoId, {'basename': key})

              var _f = [];
              _f.push(file);
              _f = _f.concat(_files.videoFiles[key] || []);
              that.addChildren(response.data, _f);
            },
          ]);
        },
        _promises
      );

      if (_promises.length > 0) {
        // Make requests for the videos
        that.chainedActions(_promises).then(function(data) {
        }, function(error) {
          console.log('ERROR chained actiοns', error);
        });
      }
    });
  };

  this.initProject = function(files) {
    var prevFiles = [];
    files = _.reject(files, function(file) {
      if (prevFiles.includes(file.key)) {
        return true;
      }
      prevFiles.push(file.key);
      return false;
    });
    return this
      .createDeposit(this.masterInit, this.masterSchema, 'project')
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

  this.createDeposit = function(url, schema, depositType, extra) {
    var data = angular.merge({}, { $schema: schema }, extra || {});
    return this.makeAction(url, depositType, 'CREATE', data);
  };

  this.makeAction = function(url, depositType, action, payload) {
    var actionInfo = depositActions[depositType][action];
    if (actionInfo.preprocess) {
      payload = actionInfo.preprocess(payload);
    };
    return cdsAPI.action(url, actionInfo.method, payload, actionInfo.headers);
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

  var checkStatus = function(task, status) {
    return function(child) {
      return child._cds.state[task] == status;
    };
  };

  var getOverallState = function(children) {
    var taskStates = {};
    if (!children.length) {
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
    that.aggregatedState = getOverallState(that.master.metadata.videos);
  });

  this.getRecordUrl = function(recid) {
    return urlBuilder.record({recid: recid});
  }

  // Listen for permission change
  $scope.$on(
    'cds.deposit.project.permissions.update',
    function(evt, _access, permissions) {
      // Broadcast down
      $scope.$broadcast(
        'cds.deposit.video.permissions.update', _access, permissions
      );
    }
  );
}

cdsDepositsCtrl.$inject = [
  '$http',
  '$q',
  '$scope',
  '$window',
  '$location',
  '$element',
  'depositStates',
  'depositActions',
  'depositSSEEvents',
  'cdsAPI',
  'urlBuilder',
  'localStorageService',
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
      // Accepted video file extensions
      videoExtensions: '@?',
    },
    controller: cdsDepositsCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    },
  };
}

angular.module('cdsDeposit.components').component('cdsDeposits', cdsDeposits());
