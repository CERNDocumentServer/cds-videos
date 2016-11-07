function cdsDepositsConfig($locationProvider) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = ['$locationProvider'];

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
      deposit.metadata._files = files || [];
      this.master = deposit;
      // Initialized
      this.initialized = true;
      if (this.master.links.html) {
        this.handleRedirect(this.master.links.html, true);
      }
    };
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
      },
      controller: cdsDepositsCtrl,
      templateUrl: function($element, $attrs) {
        return $attrs.template;
      }
    }
  };

  function cdsDeposit() {
    return {
      transclude: true,
      bindings: {
        index: '=',
        master: '@',
        // Interface related
        updateRecordAfterSuccess: '@',
        // Deposit related
        schema: '@',
        record: '=',
        links: '=',
        // The form model
        depositFormModel: '=?',
      },
      require: {
        cdsDepositsCtrl: '^cdsDeposits'
      },
      controller: function($scope, $q) {
        var that = this;
        // The deposit can have the follwoing states
        this.$onInit = function() {
          // Resolve the record schema
          this.cdsDepositsCtrl.JSONResolver(this.schema)
          .then(function(response) {
            that.schema = response.data;
          });

          this.postSuccessProcess = function(responses) {
            // Get only the latest response (in case of multiple actions)
            var response = (responses[responses.length - 1] || responses).data;
            // Update record
            if (this.updateRecordAfterSuccess) {
              this.record = angular.merge({}, this.record, response.metadata);
            }
            // Update links
            if (this.updateLinksAfterSuccess) {
              this.links = response.links;
            }
          }

          this.postErrorProcess = function(response) {
            // Process validation errors if any
            if (response.data.status === 400 && response.data.errors) {
              var deferred = $q.defer();
              var promise = deferred.promise;
              promise.then(function displayValidationErrors() {
                angular.forEach(response.data.errors, function(value) {
                  $scope.$broadcast('cds.deposit.validation.error', value);
                });
              });
              deferred.resolve();
            }
          }
        }

        this.guessEndpoint = function(endpoint) {
          if (Object.keys(that.links).indexOf(endpoint) > -1) {
            return that.links[endpoint];
          }
          return endpoint;
        };

        this.cleanData = function(data, unwanted) {
          var _unwantend = unwanted || [[null], [undefined]];
          // Delete the _files before request
          delete data._files;
          angular.forEach(data, function(value, key) {
            angular.forEach(_unwantend, function(_value) {
              if (angular.equals(_value, value))  {
                delete data[key];
              }
            });
          });
          return data;
        }

        // Do a single action at once
        this.makeSingleAction = function(endpoint, method, redirect) {
          // Guess the endpoint
          var url = this.guessEndpoint(endpoint);
          return this.cdsDepositsCtrl
          .makeAction(url, method, that.cleanData(that.record));
        }

        // Do multiple actions at once
        this.makeMultipleActions = function(actions, redirect) {
          var promises = [];
          var cleanRecord = that.cleanData(that.record);
          angular.forEach(actions, function(action, index) {
            var url = that.guessEndpoint(action[0]);
            this.push(function() {
              return that.cdsDepositsCtrl.makeAction(url, action[1], cleanRecord);
            });
          }, promises);
          return that.cdsDepositsCtrl.chainedActions(promises);
        }

        this.onSuccessAction = function(response) {
          // Post success process
          that.postSuccessProcess(response);
          // Inform the parents
          $scope.$emit('cds.deposit.success', response);
          // Make the form pristine again
          that.depositFormModel.$setPristine();
        }

        this.onErrorAction = function(response) {
          // Post error process
          that.postErrorProcess(response);
          // Inform the parents
          $scope.$emit('cds.deposit.error', response);
        }
      },
      template: "<div ng-transclude></div>"
    };
  }

  function cdsForm() {
    return {
      transclude: true,
      bindings: {
        form: '@',
      },
      require: {
        cdsDepositCtrl: '^cdsDeposit'
      },
      controller: function($scope, schemaFormDecorators) {
        var that = this;
        this.$onInit = function() {
          this.cdsDepositCtrl.depositForm = {};
          this.cdsDepositCtrl.cdsDepositsCtrl.JSONResolver(this.form)
          .then(function(response) {
            that.form = response.data;
          });

          // Add custom templates
          var formTemplates = this.cdsDepositCtrl.cdsDepositsCtrl.formTemplates;
          var formTemplatesBase = this.cdsDepositCtrl.cdsDepositsCtrl.formTemplatesBase;
          if (formTemplates && formTemplatesBase) {
            if (formTemplatesBase.substr(formTemplatesBase.length -1) !== '/') {
              formTemplatesBase = formTemplatesBase + '/';
            }

            angular.forEach(formTemplates, function(value, key) {
              schemaFormDecorators
              .decorator()[key.replace('_', '-')]
              .template = formTemplatesBase + value;
            });
          }
        };

        $scope.$on('cds.deposit.validation.error', function(evt, value) {
          $scope.$broadcast(
            'schemaForm.error.' + value.field,
            'backendValidationError',
            value.message
          );
        });

        this.removeValidationMessage = function(fieldValue, form) {
          // Reset validation only if the filed has been changed
          if (form.validationMessage) {
            // If the field has changed remove the error
            $scope.$broadcast(
              'schemaForm.error.' + form.key.join('.'),
              'backendValidationError',
              true
            );
          }
        }
      },
      templateUrl: function($element, $attrs) {
        return $attrs.template;
      }
    }
  }

  function cdsActions() {
    return {
      bindings: {
      },
      require: {
        cdsDepositCtrl: '^cdsDeposit'
      },
      controller: function($scope) {
        var that = this;
        this.$onInit = function() {
          this.postActions = function() {
            // Stop loading
            $scope.$emit('cds.deposit.loading.stop');
            that.cdsDepositCtrl.loading = false;
          }
          this.actionHandler = function(type, method) {
            // Start loading
            $scope.$emit('cds.deposit.loading.start');
            that.cdsDepositCtrl.loading = true;
            that.cdsDepositCtrl.makeSingleAction(type, method)
            .then(
              that.cdsDepositCtrl.onSuccessAction,
              that.cdsDepositCtrl.onErrorAction
            ).finally(that.postActions);
          }
          this.actionMultipleHandler = function(actions) {
            // Start loading
            $scope.$emit('cds.deposit.loading.start');
            that.cdsDepositCtrl.loading = true;
            that.cdsDepositCtrl.makeMultipleActions(actions)
            .then(
              that.cdsDepositCtrl.onSuccessAction,
              that.cdsDepositCtrl.onErrorAction
            ).finally(that.postActions);
          }
        }
      },
      templateUrl: function($element, $attrs) {
        return $attrs.template;
      }
    }
  }

  function cdsUploader() {
    return {
      bindings: {
        files: '=',
        filterFiles: '=',
      },
      require: {
        cdsDepositCtrl: '^cdsDeposit'
      },
      controller: function($scope, $q, Upload, $http) {
        var that = this;
        // Is the uploader loading
        this.loading = false;
        // The Upload Queue
        this.queue = [];
        // Do we have any errors
        this.errors = [];
        // The ongoing uploads
        this.uploading = [];

        // On Component init
        this.$onInit = function() {
          // Add any files in the queue that are not completed
          this.queue = _.reject(that.files, {completed: true});

          // Prepare file request
          this.prepareUpload = function(file) {
            var args = {
              url:  that.cdsDepositCtrl.links.bucket + '/' + file.key,
              method: 'PUT',
              headers: {
                'Content-Type': (file.type || '').indexOf('/') > -1 ? file.type : ''
              },
              data: file
            };
            return args;
          };

          this.prepareDelete = function(url) {
            var args = {
              url:  url,
              method: 'DELETE'  ,
              headers: {
                'Content-Type': 'application/json'
              }
            };
            return args;
          }

          this.uploader = function() {
            var defer = $q.defer();
            var data = [];
            function _chain(upload) {
              var args = that.prepareUpload(upload);
              Upload.http(args)
              .then(
                function success(response) {
                  // Update the file with status
                  response.data.completed = true;
                  response.data.progress = 100;
                  that.updateFile(
                    response.config.data.key,
                    response.data,
                    true
                  );
                  data.push(response.data);
                },
                function error(response) {
                  // Throw an error
                  defer.reject(response);
                },
                function progress(evt) {
                  var progress = parseInt(100.0 * evt.loaded / evt.total, 10);
                  that.cdsDepositCtrl.progress = progress;
                  // Update the file with status
                  that.updateFile(
                    evt.config.data.key,
                    {
                      progress: progress
                    }
                  );
                }
              )
              .finally(function finish(evt) {
                if (that.queue.length > 0) {
                  return _chain(that.queue.shift());
                } else {
                  defer.resolve(data);
                };
              });
            }
            _chain(that.queue.shift());
            return defer.promise;
          }

          this.upload = function() {
            if (that.queue.length > 0) {
              // Start loading
              $scope.$emit('cds.deposit.loading.start');
              that.cdsDepositCtrl.loading = true;
              // Start local loading
              that.loading = true;
              that.uploader()
              .then(
                function success(response) {
                },
                function error(response) {
                  // Inform the parents
                  $scope.$emit('cds.deposit.error', response);
                }
              ).finally(
                function done() {
                  // Stop loading
                  $scope.$emit('cds.deposit.loading.stop');
                  that.cdsDepositCtrl.loading = false;
                  // Local loading
                  that.loading = false;
                }
              );
            }
          }
        }

        this.findFileIndex = function(files, key) {
          return _.indexOf(
            files,
            _.findWhere(that.files, {key: key})
          );
        }

        this.updateFile = function(key, data, force) {
          var index = this.findFileIndex(that.files, key);
          if (force === true) {
            this.files[index] = angular.copy(data);
            return;
          };

          this.files[index] = angular.merge(
            {},
            this.files[index],
            data || {}
          );
        }

        this.addFiles = function(_files) {
          angular.forEach(_files, function(file, index) {
            // GRRRRRRRRRRR :(
            file.key = file.name;
            // Mark the file as local
            file.local = true;
            // Add the file to the list
            that.files.push(file);
            // Add the file to the queue
            that.queue.push(file);
          });
        };

        this.abort = function() {
          // Abort the upload
        };

        this.remove = function(key) {
          // Find the file index
          var index = this.findFileIndex(that.files, key);

          if (this.files[index].links === undefined) {
            // Remove the file from the list
            that.files.splice(index, 1);
            // Find the file's index in the queue
            var q_index = this.findFileIndex(that.queue, key);
            // remove the file from the queue
            that.queue.splice(q_index, 1);
          } else {
            var args = that.prepareDelete(
              that.files[index].links.version || that.files[index].links.self
            );
            $http(args)
            .then(
              function success() {
                // Remove the file from the list
                that.files.splice(index, 1);
              },
              function error(error) {
                // Inform the parents
                $scope.$emit('cds.deposit.error', response);
              }
            );
          }
        };
      },
      templateUrl: function($element, $attrs) {
        return $attrs.template;
      }
    }
  }
  angular.module('cdsDeposit', [
    'schemaForm', 'mgcrea.ngStrap',
    'mgcrea.ngStrap.modal', 'pascalprecht.translate', 'ui.sortable',
    'ui.select', 'mgcrea.ngStrap.select', 'mgcrea.ngStrap.datepicker',
    'mgcrea.ngStrap.helpers.dateParser', 'mgcrea.ngStrap.tooltip', 'ngFileUpload',
    'invenioFiles.filters'
  ])
  .config(cdsDepositsConfig)
  .component('cdsDeposits', cdsDeposits())
  .component('cdsForm', cdsForm())
  .component('cdsActions', cdsActions())
  .component('cdsUploader', cdsUploader())
  .component('cdsDeposit', cdsDeposit());
