function cdsDepositsConfig($locationProvider) {
  $locationProvider.html5Mode({
    enabled: true,
    requireBase: false,
    rewriteLinks: false,
  });
}

// Inject the necessary angular services
cdsDepositsConfig.$inject = ['$locationProvider'];


angular.module('cdsDeposit.components', []);

angular.module('cdsDeposit', [
  'cdsDeposit.components', 'schemaForm', 'mgcrea.ngStrap',
  'mgcrea.ngStrap.modal', 'pascalprecht.translate', 'ui.sortable',
  'ui.select', 'mgcrea.ngStrap.select', 'mgcrea.ngStrap.datepicker',
  'mgcrea.ngStrap.helpers.dateParser', 'mgcrea.ngStrap.tooltip', 'ngFileUpload',
  'invenioFiles.filters'
])
.config(cdsDepositsConfig);
