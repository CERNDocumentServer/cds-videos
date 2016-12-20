function cdsFormCtrl($scope, $http, $q, schemaFormDecorators) {

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

  this.types = $q.defer();

  this.autocompleteCategories = function(options, query) {
    if (!that.categories) {
      that.categories = $http.get(options.url).then(function(data) {
        var categories = data.data.hits.hits;
        that.types.resolve({ data: [].concat.apply([], categories.map(
          function (category) {
            return category.metadata.types.map(
              function (type) {
                return {
                  name: type,
                  value: type,
                  category: category.metadata.name
                };
              }
            );
          }
        ))});
        return categories.map(function(category) {
          return {
            name: category.metadata.name,
            value: category.metadata.name,
            types: category.metadata.types
          };
        });
      });
    }
    return that.categories.then(function(categories) {
      return {
        data: categories
      };
    });
  }

  this.autocompleteType = function() {
    return that.types.promise;
  }
}

cdsFormCtrl.$inject = ['$scope', '$http', '$q', 'schemaFormDecorators'];

function cdsForm() {
  return {
    transclude: true,
    bindings: {
      form: '@',
    },
    require: {
      cdsDepositCtrl: '^cdsDeposit'
    },
    controller: cdsFormCtrl,
    templateUrl: function($element, $attrs) {
      return $attrs.template;
    }
  }
}

angular.module('cdsDeposit.components')
  .component('cdsForm', cdsForm());
