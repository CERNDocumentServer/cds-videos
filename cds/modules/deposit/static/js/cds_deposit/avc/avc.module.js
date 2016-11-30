function cdsDepositsConfig(
  $locationProvider, depositStatesProvider, depositStatusesProvider
) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });
  // Initialize the states
  depositStatesProvider.setValues(
    [
      'file_download',
      'file_video_metadata_extraction',
      'file_video_extract_frames',
      'file_transcode',
    ]
  );
  depositStatusesProvider.setValues(
    {
      PENDING: 'DEPOSIT_STATE/PENDING',
      STARTED: 'DEPOSIT_STATE/STARTED',
      FAILURE: 'DEPOSIT_STATE/FAILURE',
      SUCCESS: 'DEPOSIT_STATE/SUCCESS'
    }
  );
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  '$locationProvider',
  'depositStatesProvider',
  'depositStatusesProvider',
];

angular.module('cdsDeposit.components', []);
angular.module('cdsDeposit.factories', []);

angular.module('cdsDeposit', [
  'cdsDeposit.factories','cdsDeposit.components', 'schemaForm',
  'mgcrea.ngStrap', 'mgcrea.ngStrap.modal',
  'pascalprecht.translate', 'ui.sortable',
  'ui.select', 'mgcrea.ngStrap.select', 'mgcrea.ngStrap.datepicker',
  'mgcrea.ngStrap.helpers.dateParser',
  'mgcrea.ngStrap.tooltip', 'ngFileUpload', 'monospaced.elastic',
  'invenioFiles.filters'
])
.provider("depositStates", function() {
  var states = [];
  return {
    setValues: function(values) {
      states = states.concat(values);
    },
    $get: function() {
      return states;
    }
  }
})
.provider("depositStatuses", function() {
  var statuses = {};
  return {
    setValues: function(values) {
      statuses = values;
    },
    $get: function() {
      return statuses;
    }
  }
})
.filter('toInt', function() {
  return function(input) {
    var result;
    try {
        result = parseInt(input);
    } catch(error) {
      result = input;
    }
    return result;
  };
})
.config(cdsDepositsConfig)
