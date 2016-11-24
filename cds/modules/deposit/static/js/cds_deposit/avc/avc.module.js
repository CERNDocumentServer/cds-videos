function cdsDepositsConfig($locationProvider, statesProvider) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });

  // Initialize the states
  statesProvider.setStates(
    [
      'file_download',
      'file_video_metadata_extraction',
      'file_transcode',
      'file_video_extract_frames',
    ]
  );
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = ['$locationProvider', 'statesProvider'];

angular.module('cdsDeposit.components', []);
angular.module('cdsDeposit.factories', []);
angular.module('cdsDeposit', [
  'cdsDeposit.factories','cdsDeposit.components', 'schemaForm',
  'mgcrea.ngStrap', 'mgcrea.ngStrap.modal',
  'pascalprecht.translate', 'ui.sortable',
  'ui.select', 'mgcrea.ngStrap.select', 'mgcrea.ngStrap.datepicker',
  'mgcrea.ngStrap.helpers.dateParser',
  'mgcrea.ngStrap.tooltip', 'ngFileUpload',
  'invenioFiles.filters'
])
.provider("states", function() {
  var states = [];
  return {
    setStates: function(values) {
      states = states.concat(values);
    },
    $get: function() {
      return states;
    }
  }

})
.config(cdsDepositsConfig)
