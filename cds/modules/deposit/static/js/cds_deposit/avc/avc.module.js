function cdsDepositsConfig(
  $locationProvider, depositStatesProvider, depositStatusesProvider,
  urlBuilderProvider, typeReducerProvider
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
      'update_deposit',
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
  urlBuilderProvider.setBlueprints(
    {
      "video": "/deposit/<%=deposit%>/preview/video/<%=key%>",
      "iiif": "/api/iiif/v2/<%=deposit%>:<%=key%>/full/<%=res%>/0/default.png"
    }
  )
  typeReducerProvider.setBlueprints(
    {
      "SUCCESS": function(type, data) {
        console.log('SUCCFESS PROVIDER', type, data);
        if (type === 'update_deposit') {
          this.updateDeposit(data.meta.payload.deposit);
        }
        console.log('THE STATE REPORTER', this.stateReporter);
      }
    }
  )
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = [
  '$locationProvider',
  'depositStatesProvider',
  'depositStatusesProvider',
  'urlBuilderProvider',
  'typeReducerProvider',
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
.provider("urlBuilder", function() {
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
.provider("typeReducer", function() {
  var blueprints = {};

  function setBlueprint(key, value) {
    // underscorejs templates
    blueprints[key] = value;
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
.provider("stateReducer", function() {
  var blueprints = {};

  function setBlueprint(key, value) {
    // underscorejs templates
    blueprints[key] = value;
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
.filter('progressClass', function() {
  return function(input) {
    switch (input) {
      case 'SUCCESS':
        return 'success';
      case 'STARTED':
        return 'info';
      case 'FAILURE':
        return 'danger';
      case 'PENDING':
        return 'warning';
    }
  };
})
.filter('progressIcon', function() {
  return function(input) {
    switch (input) {
      case 'SUCCESS':
        return 'fa-check';
      case 'STARTED':
        return 'fa-hourglass';
      case 'FAILURE':
        return 'fa-ban';
      case 'PENDING':
        return 'fa-pause';
    }
  };
})
.config(cdsDepositsConfig)
