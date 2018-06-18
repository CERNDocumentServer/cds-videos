function cdsDepositsConfig(
  $locationProvider,
  depositExtractedMetadataProvider,
  depositStatesProvider,
  depositStatusesProvider,
  depositActions,
  inheritedPropertiesProvider,
  taskRepresentationsProvider,
  urlBuilderProvider,
  typeReducerProvider,
  localStorageServiceProvider,
  sfErrorMessageProvider,
  jwtProvider,
  $httpProvider,
  $compileProvider
) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });
  sfErrorMessageProvider.setDefaultMessage(0, 'This field is required.');

  // Local storage configuration
  localStorageServiceProvider.setPrefix('cdsDeposit');

  var mainStatuses = [
    'file_upload',
    'file_download',
    'file_video_metadata_extraction',
    'file_video_extract_frames',
    'file_transcode',
  ];

  // Initialize the states
  depositStatesProvider.setValues(mainStatuses);

  // Initialize statuses provider
  depositStatusesProvider.setValues({
    PENDING: 'DEPOSIT_STATE/PENDING',
    STARTED: 'DEPOSIT_STATE/STARTED',
    FAILURE: 'DEPOSIT_STATE/FAILURE',
    SUCCESS: 'DEPOSIT_STATE/SUCCESS',
    REVOKED: 'DEPOSIT_STATE/REVOKED',
  });

  // Initialize extracted metadata pre-fill
  depositExtractedMetadataProvider.setValues({
    values:{
      'title': function(deposit, metadata){
        if('title' in metadata){
          deposit.title = {title: metadata.title};
          return metadata.title;
        }
      },
      'description': function(deposit, metadata){
        if('description' in metadata){
          deposit.description = metadata.description;
          return metadata.description;
        }
      },
      'keywords': function(deposit, metadata){
        if('keywords' in metadata){
          deposit.keywords = metadata.keywords.map(function(keyword){
            return {name: keyword, value: {name: keyword}};
          });
          return metadata.keywords.join(', ');
        }
      },
      'date': function(deposit, metadata){
        if('creation_time' in metadata){
          deposit.date = new Date(metadata.creation_time).toISOString().slice(0,10);
          return deposit.date;
        }
      },
    }
  });

  // Deposit actions' information
  depositActions.setValues(['project', 'video'])

  inheritedPropertiesProvider.setValues([
    'contributors',
    'date',
    'description',
    'keywords',
    'license',
    'title.title',
    'translations',
  ]);

  taskRepresentationsProvider.setValues({
    file_upload: 'Video file upload',
    file_download: 'Video file download',
    file_transcode: 'Video transcoding',
    file_video_extract_frames: 'Video frame extraction',
    file_video_metadata_extraction: 'Video metadata extraction'
  });

  // Initialize url builder
  urlBuilderProvider.setBlueprints({
    iiif: '/api/iiif/v2/<%=deposit%>:<%=version_id%>:<%=key%>/full/!<%=res%>/0/default.png',
    categories: '/api/categories',
    video: '/deposit/<%=deposit%>/preview/video/<%=key%>',
    eventInfo: '/hooks/receivers/avc/events/<%=eventId%>',
    restartEvent: '/hooks/receivers/avc/events/<%=eventId%>/tasks/<%=taskId%>',
    taskFeedback: '/hooks/receivers/avc/events/<%=eventId%>/feedback',
    selfVideo: '/api/deposits/video/<%=deposit%>',
    bucketVideo: '/api/files/<%=bucket%>',
    actionVideo: '/api/deposits/video/<%=deposit%>/actions/<%=action%>',
    record: '/record/<%=recid%>',
  });

  // Initialize type reducer
  typeReducerProvider.setBlueprints({
    SUCCESS: function(type, data) {
      if (type === 'update_deposit') {
        this.updateDeposit(data.meta.payload.deposit);
      }
    },
  });

  // JWT Token
  // Search DOM if exists
  var authorized_token = document.getElementsByName('authorized_token');
  if (authorized_token.length > 0) {
    token = authorized_token[0].value;
    // No cache on API requests
    var headers = {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/json',
    };
    // Add no cache on all ``GET`` requests
    var _get = _.merge(
      headers,
      {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': 0
      }
    );
    jwtProvider.setHeader(_get);
    $httpProvider.defaults.headers['delete'] = headers;
    $httpProvider.defaults.headers['post'] = headers;
    $httpProvider.defaults.headers['put'] = headers;
  }

  // Optimize Angular on production
  // $compileProvider.debugInfoEnabled(false);
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  '$locationProvider',
  'depositExtractedMetadataProvider',
  'depositStatesProvider',
  'depositStatusesProvider',
  'depositActionsProvider',
  'inheritedPropertiesProvider',
  'taskRepresentationsProvider',
  'urlBuilderProvider',
  'typeReducerProvider',
  'localStorageServiceProvider',
  'sfErrorMessageProvider',
  'jwtProvider',
  '$httpProvider',
  '$compileProvider',
];

// Register modules
angular.module('cdsDeposit.filters', []);
angular.module('cdsDeposit.providers', []);
angular.module('cdsDeposit.components', []);
angular.module('cdsDeposit.factories', []);

// Register all cdsDeposit module into one
angular.module('cdsDeposit.modules', [
  'cdsDeposit.filters',
  'cdsDeposit.providers',
  'cdsDeposit.factories',
  'cdsDeposit.components',
  'LocalStorageModule',
  'schemaForm',
]).config(cdsDepositsConfig);

angular
  .module('cdsDeposit.filters')
  .filter('taskRepr', function(taskRepresentations) {
    return function(input) {
      return taskRepresentations[input] || input;
    };
  });

angular.module('schemaForm')
  .controller('invenioDynamicSelectController', ['$scope', '$controller', '$select', '$http',
    function ($scope, $controller, $select, $http) {
      $controller('dynamicSelectController', {$scope: $scope});

      // Formats tags tokens in ``uiselectmultiple``
      $scope.form.formatTokenTags = function(item) {
        return {
          name: item,
          value: {
            name: item
          }
        }
      }

      // Use this only in multiple select
      if ($scope.form.type === 'uiselectmultiple') {
        // store the $scope form as is not accesible inside the handler's scope below
        var form = $scope.form;
        $scope.$on('cds.deposit.form.keywords.inherit', function(event, record) {
          form.internalModelTags = record.keywords;
        });
      }

      if ($scope.modelArray) {
        $scope.$watchCollection('modelArray', function (newValue) {
          // If this is not the initial setting of the element...
          if (!angular.equals($scope.select_model, {})) {
            // Get the element's correct value from the array model
            var formKey = $scope.form.key.slice(-1)[0],
                value = $scope.modelArray[$scope.arrayIndex][formKey];
            // Set ui-select's model to the correct value if needed
            if (value && $scope.insideModel !== value) {
              $scope.insideModel = value;
              var query = $scope.$eval($scope.form.options.processQuery || 'query', {query: value});
              $scope.populateTitleMap($scope.form, query);
              $scope.select_model.selected = $scope.find_in_titleMap(value);
            }
          }
        });
      }
    }]);
// Initialize the module
angular
  .module('cdsDeposit', [
    'cdsDeposit.modules',
    'schemaForm',
    'mgcrea.ngStrap',
    'mgcrea.ngStrap.modal',
    'pascalprecht.translate',
    'ui.sortable',
    'ui.select',
    'mgcrea.ngStrap.select',
    'mgcrea.ngStrap.datepicker',
    'mgcrea.ngStrap.helpers.dateParser',
    'mgcrea.ngStrap.tooltip',
    'ngFileUpload',
    'monospaced.elastic',
    'invenioFiles.filters',
    'afkl.lazyImage',
    'hl.sticky',
    'duScroll',
    'toaster',
    'angular-loading-bar',
  ]);
