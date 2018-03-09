function cdsDepositsCtrl(
  $http,
  $q,
  $scope,
  $window,
  $location,
  $element,
  $interval,
  depositStates,
  cdsAPI,
  urlBuilder,
  localStorageService,
  toaster,
  jwt
) {
  var that = this;
  this.edit = false;

  // The master deposit
  this.master = {};
  // Global loading state
  this.loading = false;
  // The access rights
  this.accessRights = {};
  // The last video upload promise
  this.lastVideoUpload = $q.resolve();

  // Schemas and forms
  that.masterSchemaResolved = {};
  that.childrenSchemaResolved = {};
  that.childrenFormResolved = {};
  that.masterFormResolved = {};

  // Interval Autoupdate
  this.autoUpdateInterval = null;

  this.$onDestroy = function() {
    try {
      $interval.cancel(that.autoUpdateInterval);
      // On destroy delete the event listener
      delete $window.onbeforeunload;
    } catch (error) {}
  };

  this.initState = {
    PENDING: [],
    STARTED: [],
    FAILURE: [],
    SUCCESS: [],
    REVOKED: [],
  }
  // Show message when window is closing
  this.onExit = false;

  // Fetch the latest record data (only if it's a project)
  this.fetchRecord = function() {
    // Fetch only if it is in ``draft`` mode
    if (that.master.metadata._deposit.status === 'draft') {
      cdsAPI.action(that.master.links.self || that.masterLinks.self , 'GET', {}, jwt).then(function(data) {
        // Metadata for the project
        $scope.$broadcast(
          'cds.deposit.metadata.update.' + data.data.metadata._deposit.id,
          data.data.metadata
        );
        // Metadata for the videos
        data.data.metadata.videos.forEach(function(_metadata) {
          $scope.$broadcast(
            'cds.deposit.metadata.update.' + _metadata._deposit.id,
            _metadata
          );
        })
      });
    }
  }

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
      this.master = cleanUpInputDeposit(deposit);
      // Initialized
      this.initialized = true;
      // Start sync metadata
      that.autoUpdateInterval = $interval(that.fetchRecord, 15000);
      if (this.master.links.html) {
        this.handleRedirect(this.master.links.html, true);
      }
    }

    function cleanUpInputDeposit(deposit) {
      // add empty `keywords` field if missing, to avoid issue of keywords not added/saved
      if (deposit.metadata) {
        if (!('keywords' in deposit.metadata)) {
          deposit.metadata.keywords = [];
        }
        if (deposit.metadata.videos) {
          deposit.metadata.videos.map(function (video) {
            if (!(video.keywords)) {
              video.keywords = [];
            }
            return video;
          });
        }
      }
      return deposit;
    }
  };

  this.addChildren = function(deposit, files) {
    deposit.metadata._files = files || [];
    this.master.metadata.videos.push(deposit.metadata);
  };

  this.isVideoFile = function(key) {
    var videoExtensions = (that.videoExtensions || 'mp4,mkv,mov').split(',');
    var fileKey = null;
    videoExtensions.forEach(function(ext) {
      if (key.toLowerCase().endsWith(ext.toLowerCase())) {
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
    var partition = _.partition(files, function(f) {
        return that.isVideoFile(f.name);
      }),
      // Index videos by their key
      videos = _.keyBy(partition[0], function(video) {
        return that.isVideoFile(video.name);
      }),
      other = partition[1];

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

  this.addFiles = function(files, invalidFiles) {
    // Do nothing if files array is empty
    if (!files) {
      return;
    }
    // remove invalid files
    files = _.difference(files, invalidFiles || []);
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
      var master_id = that.master.metadata._deposit.id;

      // Build the promises
      var _promises = [];
      // Find already uploaded videos
      var uploadedVideos = that.master.metadata.videos
        .map(function(deposit) {
          if (deposit._files && deposit._files.length > 0) {
            // Find the master
            var _f = _.find(deposit._files, {'context_type': 'master'});
            return (!_.isEmpty(_f)) ? _f.key : undefined;
          }
        })
        .filter(function(key) {
          return key != undefined;
        });
      var videoKeys = _.keys(_files.videos).map(function (name) {
        return _files.videos[name].key;
      });

      that.duplicateVideos = _.intersection(videoKeys, uploadedVideos);
      _files.videos = _.omitBy(_files.videos, function (val) {
        return that.duplicateVideos.includes(val.key)
      });

      // Send an alert for duplicate videos
      if (that.duplicateVideos.length > 0) {
        toaster.pop({
          type: 'error',
          title: 'Duplicate video(s)!',
          body: that.duplicateVideos.join(', '),
          bodyOutputType: 'trustedHtml',
        });
      }

      if ((invalidFiles || []).length > 0) {
        // Push a notification
        toaster.pop({
          type: 'error',
          title: 'Invalid file(s)',
          body: _.map(invalidFiles, 'name').join(', '),
          bodyOutputType: 'trustedHtml'
        });
      }
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
        cdsAPI
          .chainedActions(_promises)
          .then(
            function(data) {},
            function(error) {}
          );
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
    return cdsAPI.makeAction(url, depositType, 'CREATE', data);
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
      return child._cds.state[task] === status;
    };
  };

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
  '$interval',
  'depositStates',
  'cdsAPI',
  'urlBuilder',
  'localStorageService',
  'toaster',
  'jwt',
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
      // Show restricted fields
      showAvcRestrictedFields: '=?',
      // Show admin Interface
      showAdminInterface: '=?',
    },
    controller: cdsDepositsCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    },
  };
}

angular.module('cdsDeposit.components').component('cdsDeposits', cdsDeposits());
