function cdsDepositsConfig(
  $locationProvider,
  depositStatesProvider,
  depositSSEEventsProvider,
  depositStatusesProvider,
  inheritedPropertiesProvider,
  errorRepresentationsProvider,
  urlBuilderProvider,
  typeReducerProvider
) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });

  var mainStatuses = [
    'file_download',
    'file_video_metadata_extraction',
    'file_video_extract_frames',
    'file_transcode',
  ];

  // Initialize the states
  depositStatesProvider.setValues(mainStatuses);

  var additionalEvents = [ 'update_deposit' ];

  // Extra SSE events to listen excluded from the statuses
  depositSSEEventsProvider.setValues(mainStatuses.concat(additionalEvents));

  // Initialize statuses provider
  depositStatusesProvider.setValues({
    PENDING: 'DEPOSIT_STATE/PENDING',
    STARTED: 'DEPOSIT_STATE/STARTED',
    FAILURE: 'DEPOSIT_STATE/FAILURE',
    SUCCESS: 'DEPOSIT_STATE/SUCCESS',
    REVOKED: 'DEPOSIT_STATE/REVOKED',
  });

  inheritedPropertiesProvider.setValues([
    'title.title',
    'description.value',
    'contributors'
  ]);

  errorRepresentationsProvider.setValues({
    file_download: 'Video file download error',
    file_transcode: 'Video transcoding error',
    file_video_extract_frames: 'Video frame extraction error',
    file_video_metadata_extraction: 'Video metadata extraction error'
  });

  // Initialize url builder
  urlBuilderProvider.setBlueprints({
    iiif: '/api/iiif/v2/<%=deposit%>:<%=key%>/full/<%=res%>/0/default.png',
    sse: '/api/deposits/project/<%=id%>/sse',
    video: '/deposit/<%=deposit%>/preview/video/<%=key%>',
  });

  // Initialize type reducer
  typeReducerProvider.setBlueprints({
    SUCCESS: function(type, data) {
      if (type === 'update_deposit') {
        this.updateDeposit(data.meta.payload.deposit);
      }
    },
  });
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  '$locationProvider',
  'depositStatesProvider',
  'depositSSEEventsProvider',
  'depositStatusesProvider',
  'inheritedPropertiesProvider',
  'errorRepresentationsProvider',
  'urlBuilderProvider',
  'typeReducerProvider',
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
]);

angular
  .module('cdsDeposit.filters')
  .filter('errorRepr', function(errorRepresentations) {
    return function(input) {
      return errorRepresentations[input] || input;
    };
  });

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
  ])
  .config(cdsDepositsConfig);
