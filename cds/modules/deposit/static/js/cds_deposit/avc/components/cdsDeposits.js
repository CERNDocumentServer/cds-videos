function cdsDepositsCtrl($http, $q, $scope, $window, $location) {
  var that = this;
  this.edit = false;
  // The deposit forms
  this.depositForms = [];
  // The master deposit
  this.master = {};
  // The children deposit
  this.children = [];
  // Alerts
  this.alerts = [];
  // Global loading state
  this.loading = false;

  this.$onInit = function() {
    if (this.masterLinks) {
      // Set mode to edit
      this.edit = true;
      // Fetch the project
      this.JSONResolver(this.masterLinks.self)
      .then(
        function success(response) {
          that.addMaster(response.data);
          that.initialized = true;
          // FIXME: Remove me when the project dereferencing the videos
          angular.forEach(response.data.metadata.videos, function(video, index) {
            that.JSONResolver(video.$reference)
            .then(
              function success(response){
                that.children.push(response.data);
              },
              function error(response) {

              }
            );
          })
        },
        function error(response) {

        }
      );
    }
  }

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
    // Event Listener
    this.sseEventListener = function(evt) {
      // Do some magic
      var data = JSON.parse(evt.data || '{}');
      console.log('EVENT DATA', data);
      // Send the event dynamicly to the deposit_id
      var deposit_ = 'sse.event.' + data.meta.payload.deposit_id;
      $scope.$broadcast(deposit_, data);
    }

    // SSE stuff - move to somewhere else
    var parser = document.createElement('a');
    if (this.masterLinks !== undefined) {
      parser.href = this.masterLinks.html;
    } else {
      parser.href = this.master.links.html;
    }
    console.log('PARSER', parser.pathname);
    var did = parser.pathname.split('/')[2];
    that.sseListener = new EventSource('/api/deposits/' + did + '/sse');
    console.log('THE LISTENER', that.sseListener);

    that.sseListener.onmessage = function(msg) {
      console.log('On message', msg);
    }
    that.sseListener.onerror = function(msg) {
      console.log('On errro', msg);
    }
    that.sseListener.onopen = function(msg) {
      console.log('On oepn', msg);
    }
    that.sseListener.addEventListener(
      'file_download', that.sseEventListener, false
    );
    // SSE stuff - move to somewhere else
    // SSE
  };

  this.addChildren = function(deposit, files) {
    deposit.metadata._files = files || [];
    this.children.push(deposit);
  };

  this.filterOutFiles = function(files) {
    // Logic to separated
    var videoRegex = /(.*)\.(mp4|mov)$/;
    var _files = {
      project: [],
      videos: {},
      videoFiles: {}
    }
    angular.forEach(files, function(file, index) {
      var match = file.name.match(videoRegex);
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
  }

  this.initDeposit = function(files) {

    // Filter files by videos and project
    var _files = this.filterOutFiles(files);

    // first create master
    this.createDeposit(this.masterInit, this.masterSchema)
    .then(function(response) {
      // Create the master
      that.addMaster(response.data, _files.project);
      var master_id = response.data.metadata._deposit.id;
      // for each files create child
      angular.forEach(_files.videos, function(file, key) {
        that.createDeposit(
          that.childrenInit,
          that.childrenSchema,
          {_project_id: master_id}
        )
        .then(function(response) {
          var _f = [];
          _f.push(file);
          _f = _f.concat(_files.videoFiles[key] || []);
          that.addChildren(response.data, _f);
        });
      });
      // FIXME: Add a central function to deal with it
      // Update the master record with the references
      that.JSONResolver(that.master.links.self).then(
        function success(response) {
          that.master = angular.merge(response.data, that.master);
        });
      });
    }

    this.createDeposit = function(url, schema, extra) {
      var data = angular.merge(
        {},
        {$schema: schema},
        extra || {}
      );
      return $http({
        url: url,
        method: 'POST',
        data: data
      });
    };

    this.makeAction = function(url, method, payload) {
      return $http({
        url: url,
        method: method,
        data: payload
      });
    };

    this.chainedActions = function(promises) {
      var defer = $q.defer();
      var data = [];
      function _chain(fn) {
        fn().then(
          function(_data) {
            data.push(_data);
            if (promises.length > 0) {
              return _chain(promises.shift());
            } else {
              defer.resolve(data);
            }
          }, function(error) {
            defer.reject(error);
          }
        );
      }
      _chain(promises.shift());
      return defer.promise;
    };

    this.handleRedirect = function(url, replace) {
      if (!angular.isUndefined(url) && url !== '') {
        if (replace) {
          // ¯\_(ツ)_/¯ https://github.com/angular/angular.js/issues/3924
          var parser = document.createElement('a');
          parser.href = url;
          $location.url(parser.pathname);
          $location.replace();
        } else {
          $window.location.href = url;
        }
      }
    }

    this.JSONResolver = function(url) {
      return $http.get(url);
    };

    this.dismissAlert = function(alert) {
      delete this.alerts[_.indexOf(this.alerts, alert.alert)];
    }

    // Meessages Success
    $scope.$on('cds.deposit.success', function(evt, response) {
      that.alerts = [];
      that.alerts.push({
        message: response.status || 'Success',
        type: 'success'
      });
    });
    // Meessages Error
    $scope.$on('cds.deposit.error', function(evt, response) {
      that.alerts = [];
      that.alerts.push({
        message: response.data.message,
        type: 'danger'
      });
    });
    // Loading Start
    $scope.$on('cds.deposit.loading.start', function(evt) {
      that.loading = true;
    });
    // Loading Stopped
    $scope.$on('cds.deposit.loading.stop', function(evt) {
      that.loading = false;
    });
  }

  cdsDepositsCtrl.$inject = ['$http', '$q', '$scope', '$window', '$location'];

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
      },
      controller: cdsDepositsCtrl,
      templateUrl: function($element, $attrs) {
        return $attrs.template;
      }
    }
  }

angular.module('cdsDeposit.components')
  .component('cdsDeposits', cdsDeposits());
