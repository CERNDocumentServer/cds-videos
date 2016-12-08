function cdsDepositsConfig(
  $locationProvider, depositStatesProvider, depositStatusesProvider,
  previewerURLBuilderProvider
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
  previewerURLBuilderProvider.setBlueprints(
    {
      "video": "/deposit/<%=deposit%>/preview/video/<%=key%>"
    }
  )
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  '$locationProvider',
  'depositStatesProvider',
  'depositStatusesProvider',
  'previewerURLBuilderProvider',
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
.provider("previewerURLBuilder", function() {
  var blueprints = {};

  function setBlueprint(key, value) {
    // underscorejs templates
    blueprints[key] = _.template(value);
  }
  return {
    setBlueprints: function(blueprints_) {
      angular.forEach(blueprints_, function(value, key) {
        setBlueprint(key, value);
      })
    },
    $get: function() {
      return blueprints;
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
.filter('splitText', function() {
  return function(input, by) {
    var text
    try {
      text = input.split(by).join(' ');
    } catch(error) {
      text = input;
    }
    return text;
  };
})
.config(cdsDepositsConfig)
