function cdsFormCtrl($scope, $http, $q, schemaFormDecorators) {

  var that = this;

  // Default options for schema forms
  this.sfOptions = {
    formDefaults: {
      readonly: '$ctrl.cdsDepositCtrl.isPublished()',
      disableSuccessState: true,
      feedback: false,
      startEmpty: true,
      onChange: '$ctrl.removeValidationMessage(modelValue,form)',
      ngModelOptions: {
        updateOn: 'default blur',
        allowInvalid: true
      }
    }
  }

  this.$onInit = function() {

    this.checkCopyright = function(value, form) {
      if (that.cdsDepositCtrl.cdsDepositsCtrl.copyright) {
        if ((value || '').toLowerCase() ===
            that.cdsDepositCtrl.cdsDepositsCtrl.copyright.holder.toLowerCase()) {
          that.cdsDepositCtrl.record.copyright = angular.merge(
            {},
            that.cdsDepositCtrl.cdsDepositsCtrl.copyright
          );
        }
      }
    }

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

  $scope.$on('cds.deposit.validation.error', function(evt, value, depositId) {
    if (that.cdsDepositCtrl.id == depositId &&
      !that.cdsDepositCtrl.noValidateFields.includes(value.field)) {
      $scope.$broadcast(
        'schemaForm.error.' + value.field,
        'backendValidationError',
        value.message
      );
    }
  });

  // Set form dirty when reordering UI-sortable arrays.
  this.onSortableReorder = function(event, ui) {
    that.cdsDepositCtrl.setDirty();
  }

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

  // Wrapper for functions used for autocompletion
  function autocomplete(paramsProvider, responseHandler) {
    return function(options, query) {
      if (query) {
        return $http.get(options.url, {
          params: paramsProvider(query, options)
        }).then(function(data) {
          return {data: responseHandler(data, query).slice(0, 10)};
        });
      } else {
        return $q.when({data: []});
      }
    };
  }

  /**
   * Licences
   */
  this.autocompleteLicenses = autocomplete(
    // Parameters provider
    function(query) {
      return {"text": query};
    },
    // Response handler
    function(data) {
      return data.data['text'][0]['options'].map(function(license) {
          var value = license['payload'].id;
          return {text: value, value: value};
        });
    }
  );

  /**
   * Keywords
   */
  function formKeyword(name, key_id) {
    var value = {name: name};
    if (key_id) { value.key_id = key_id }
    return {
      name: name,
      value: value
    };
  }

  this.autocompleteKeywords = autocomplete(
    // Parameters provider
    function(query) {
      return {"suggest-name": query};
    },
    // Response handler
    function(data, query) {
      var userInput = formKeyword(query);
      var suggestions =
        data.data['suggest-name'][0]['options']
          .concat(that.cdsDepositCtrl.record.keywords || [])
          .map(function(keyword) {
            return formKeyword(
              (keyword.payload) ? keyword.payload.name : keyword.name,
              (keyword.payload) ? keyword.payload.key_id : keyword.key_id
            );
          });
      prependUserInput(userInput, suggestions);
      return suggestions;
    }
  );

  /**
   * Authors
   */
  function formAuthor(author) {
    return {
      text: stripCommas(author.name),
      value: author,
      name: author.name
    };
  }

  function authorFromUser(query) {
    var re = /^(\w*,\s\w*):\s(\w*)$/
    var [fullName, affiliation] = query.split(re).splice(1, 2)
    if (!(fullName && affiliation)) {
      return null;
    }
    return formAuthor({
      name: fullName,
      affiliations: [affiliation],
    });
  }

  this.autocompleteAuthors = autocomplete(
    // Parameters provider
    function(query, options) {
      var userInput = authorFromUser(query);
      if (userInput) {
        query = userInput.name;
      }
      return angular.merge({
        query: stripCommas(query)
      }, options.extraParams);
    },
    // Response handler
    function(data, query) {
      var userInput = authorFromUser(query);
      var suggestions = data.data.map(function (author) {
        var fullName = (author.lastname || '') + ', ' +
                       (author.firstname || '');
        var valueObj = {
          name: fullName
        };

        if (author.affiliation) {
          valueObj.affiliations = [author.affiliation];
        }
        if (author.email) {
          valueObj.email = author.email;
        }
        valueObj.ids = _.reduce({
          cernccid: 'cern', recid: 'cds', inspireid: 'inspire'
        }, function(acc, newName, oldName) {
          if (author.hasOwnProperty(oldName)) {
            acc.push({ value: author[oldName], source: newName });
          }
          return acc;
        }, []);
        return formAuthor(valueObj);
      });

      prependUserInput(userInput, suggestions);

      return suggestions;
    }
  );

  /**
   * Categories and Types
   */
  this.types = $q.defer();
  this._categories = {}
  this.autocompleteCategories = function(options, query) {
    if (!that.categories) {
      that.categories = $http.get(options.url).then(function(data) {
        var categories = that._categories = data.data.hits.hits;
        // Init permissions
        that.initPermissions();
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

  /**
   * Utilities
   */
  function stripCommas(string) {
    return string.replace(/,/g, '');
  }

  // Prepends user input as custom field, if not already pre-defined
  function prependUserInput(userInput, suggestions) {
    if (userInput && _.findIndex(suggestions, function (suggestion) {
      return suggestion.name.toUpperCase() === userInput.name.toUpperCase();
    }) == -1) {
      suggestions.unshift(userInput);
    }
  }

  this.getPermissionsFromCategory = function() {
    if (that.cdsDepositCtrl.record.category) {
      that.cdsDepositCtrl.cdsDepositsCtrl.accessRights = _.first(
        _.filter(that._categories, function(_access) {
          if (_access.metadata.name === that.cdsDepositCtrl.record.category) {
            return _access;
          }
        })
      );
    }
  }

  // Init permissions
  this.initPermissions = function() {
    // Get permissions from category
    this.getPermissionsFromCategory();
    if (that.cdsDepositCtrl.record.category) {
      that.permissions = (
        !that.cdsDepositCtrl.record._access.read &&
        that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.public)
        ? 'public' : 'restricted';
    }
  }

  // Get access rights based on category
  this.setPermissions = function(modelValue, form) {
    // Get new access rights
    this.getPermissionsFromCategory();
    // Set permission for the new access rights
    that.permissions =
      that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.public
        ? 'public' : 'restricted';
    // Change Access
    that.changeAccess();
  }

  // Handle change of access rights
  this.changeAccess = function() {
    // Delete any previous permissions
    delete that.cdsDepositCtrl.record._access.read;
    // If is restricted then copy the access
    if (that.permissions === 'restricted') {
      that.cdsDepositCtrl.record._access.read = angular.copy(
        that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.restricted
      );
    }
    // Set the form dirty
    that.cdsDepositCtrl.setDirty();
    // Update permissions to videos
    if (that.cdsDepositCtrl.master) {
      $scope.$emit(
        'cds.deposit.project.permissions.update', that.cdsDepositCtrl.record._access, that.permissions
      );
    }
  }

  // Listen for permission change
  $scope.$on('cds.deposit.video.permissions.update', function(evt, _access, permissions) {
    if (!that.cdsDepositCtrl.master) {
      // Set the access
      that.cdsDepositCtrl.record._access = angular.copy(
        _access || {}
      );
      // Set the permissions
      that.permissions = angular.copy(permissions);
      // Set the form dirty
      that.cdsDepositCtrl.setDirty();
    }
  });
}

cdsFormCtrl.$inject = [
  '$scope',
  '$http',
  '$q',
  'schemaFormDecorators'
];

function cdsForm() {
  return {
    transclude: true,
    bindings: {
      form: '=',
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
