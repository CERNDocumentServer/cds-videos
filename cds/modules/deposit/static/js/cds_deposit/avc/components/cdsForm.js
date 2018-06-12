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

    // Show resticted fields
    that.showRestricted = that.cdsDepositCtrl.cdsDepositsCtrl.showAvcRestrictedFields;

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

    this.cdsDepositCtrl.cdsDepositsCtrl.categoriesPromise.then(function(hits) {
      that._categories = hits;
      that.initPermissions();
    });
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

  this.removeValidationMessage = function(fieldValue, form) {
    // If the field has changed remove the error
    $scope.$broadcast(
      'schemaForm.error.' + form.key.join('.'),
      'backendValidationError',
      true
    );
    // This removes the error from the whole array, this is for now applies
    // to ``contributors`` because we change the whole object instead of
    // an attribute (i.e. ``name``).
    if (form.key && form.key[0] === 'contributors') {
      var errorKey = _.clone(form.key || [])
      errorKey.splice(-1, 1);
      $scope.$broadcast(
        'schemaForm.error.' + errorKey.join('.'),
        'tv4-302',
        true
      );
    }
  }

  // Wrapper for functions used for autocompletion
  function autocomplete(paramsProvider, responseHandler, resultSize) {
    if (!resultSize) {
      resultSize = 10;
    }
    return function(options, query) {
      if (query) {
        return $http.get(options.url, {
          params: paramsProvider(query, options)
        }).then(function(data) {
          return {data: responseHandler(data, query).slice(0, resultSize)};
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
        return {
          text: value,
          value: value
        };
      });
    }
  );

  /**
   * Keywords
   */
  function selectMultiple(name, key_id) {
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
      var userInput = selectMultiple(query);
      var suggestions =
        data.data['suggest-name'][0]['options']
          .concat(that.cdsDepositCtrl.record.keywords || [])
          .map(function(keyword) {
            return selectMultiple(
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
      name: author.name,
      email: author.email
    };
  }

  function authorFromUser(query) {
    // Match Lastname, Firstname
    // i.e. Uni Uni , Corn Corn
    // return (3) [" Uni Uni , Corn Corn ", " Uni Uni ", " Corn Corn ", index: 0, input: " Uni Uni , Corn Corn"]
    var re = /^(.*),(.*)$/,
        authorName = query.match(re);

    if (!authorName || authorName.length !== 3) {
      return null;
    }

    return formAuthor({
      name: authorName[1].trim() + ',' + authorName[2].trim()
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
        var valueObj = {};

        if (author.firstname) {
          valueObj.name = (author.lastname || '') + ', ' +
            (author.firstname || '');
        } else {
          valueObj.name = (author.name) || '';
        }

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
    },
    50
  );

  this.onRemoveValue = function(item, model, path) {
    _.set(
      that.cdsDepositCtrl.record,
      path,
      _.pull(
        _.get(that.cdsDepositCtrl.record, path),
        item
      )
    );
    // Make it dirty
    that.cdsDepositCtrl.setDirty();
  }

  this.onSelectValue = function(item, model, path) {
    var newValue = _.concat(
      (_.get(that.cdsDepositCtrl.record, path) || []),
      model
    );
    _.set(that.cdsDepositCtrl.record, path, newValue);
    // Make it dirty
    that.cdsDepositCtrl.setDirty();
  }

  this.autocompleteAccess = _.debounce(function(query) {
    var userInput = query.length ? [{ name: query, email: query, isUserInput: true }] : [],
      options = {
        url: '//cds.cern.ch/submit/get_authors',
        extraParams: {
          'relative_curdir': 'cdslabs/videosegroups'
        }
      };

    that.accessSuggestions = userInput;

    that.autocompleteAuthors(options, query).then(function(results) {
      // put the current query as first if no results found for custom input
      var mappedResults = results.data.map(function(res) {
            return {
              name: res.value.name,
              email: res.value.email,
              isUserInput: false
            }
          });
      that.accessSuggestions = _.concat(userInput, mappedResults);
    });
  }, 300);

  /**
   * Categories and Types
   */
  this.types = $q.defer();
  this._categories = {};
  this.autocompleteCategories = function(options, query) {
    if (!that.categories) {
      var deposits = that.cdsDepositCtrl.cdsDepositsCtrl;
      that.categories = deposits.categoriesPromise.then(function() {
        var categories = that._categories;
        that.types.resolve({ data: [].concat.apply([], categories.map(
          function (category) {
            // Legacy and Migration ``type`` work around
            // Check if it has current ``type`` and if it's not part of the types
            // this means it is a legacy type and we should include it into
            // the list just for preservation proposes. Please note that
            // this value will not be visible again if you change the ``type``
            // and refresh the page.
            if (that.cdsDepositCtrl.record.type) {
              var index = category.metadata.types.indexOf(that.cdsDepositCtrl.record.type);
              if (index === -1) {
                category.metadata.types.push(that.cdsDepositCtrl.record.type);
              }
            }
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
    try {
      if (userInput && _.findIndex(suggestions, function (suggestion) {
        return suggestion.name.toUpperCase() === userInput.name.toUpperCase();
      }) == -1) {
        suggestions.unshift(userInput);
      }
    } catch(e) {

    }
  }

  this.getPermissionsFromCategory = function() {
    var master = that.cdsDepositCtrl.cdsDepositsCtrl.master;
    if (master && master.metadata) {
      that.cdsDepositCtrl.cdsDepositsCtrl.accessRights = _.first(
        _.filter(that._categories, function(_access) {
          if (_access.metadata.name === master.metadata.category) {
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
    var masterData = that.cdsDepositCtrl.cdsDepositsCtrl.master.metadata;
    if (masterData && masterData.category) {
      try {
        that.permissions = (
          !that.cdsDepositCtrl.record._access.read &&
          that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.public)
          ? 'public' : 'restricted';
      } catch (e) {
          that.permissions = 'public';
      }
    }
  }

  this.isAnyVideoAlreadyPublished = function () {
    var depositsCtrl = that.cdsDepositCtrl.cdsDepositsCtrl,
      project = depositsCtrl.master.metadata,
      videos = project.videos;
    return videos
      .filter(function (video) {
        // if it has recid, it means it has been published at least one time
        return video.recid;
      }).length > 0;
  }

  this.updateCategory = function(modelValue, form) {
    // invalidate any previously selected type
    that.cdsDepositCtrl.record.type = undefined;
    updateCategoryTypeAndPermissions();
  }

  this.updateType = function(modelValue, form) {
    updateCategoryTypeAndPermissions();
  }

  // category or type changed
  function updateCategoryTypeAndPermissions() {
    if (that.cdsDepositCtrl.depositType === 'project') {
      updatePermissions();
      that.applyNewAccessRights();

      $scope.$broadcast('cds.deposit.project.saveAll');
      $scope.$broadcast('cds.deposit.pristine.all');
    }
  }

  function updatePermissions() {
    // Get new access rights
    that.getPermissionsFromCategory();
    // Set permission for the new access rights
    that.permissions =
      that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.public
        ? 'public' : 'restricted';
  }

  // Compute new access rights and emit event to update all videos
  this.applyNewAccessRights = function() {
    // Delete any previous permissions to read (if exists), without changing the update permissions
    if (that.cdsDepositCtrl.record._access) {
      delete that.cdsDepositCtrl.record._access.read;
      delete that.cdsDepositCtrl.record._access.update;
    }
    var responsible = angular.copy(
      that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.responsible
    );
    that.cdsDepositCtrl.record._access.update = [that.cdsDepositCtrl.record._cds.current_user_mail];

    if (responsible) {
      that.cdsDepositCtrl.record._access.update = that.cdsDepositCtrl.record._access.update.concat(responsible);
    }
    // Update also the shared access tags
    that.selectedShare = that.cdsDepositCtrl.record._access.update;

    that.selectedRestricted = [];
    // If is restricted then copy the access
    if (that.permissions === 'restricted') {
      if (!that.cdsDepositCtrl.record._access){
          that.cdsDepositCtrl.record._access = {}
      }
      that.cdsDepositCtrl.record._access.read = angular.copy(
        that.cdsDepositCtrl.cdsDepositsCtrl.accessRights.metadata.access.restricted
      );

      // Update also the model
      that.selectedRestricted = that.cdsDepositCtrl.record._access.read;
    }
    // Set the form dirty
    that.cdsDepositCtrl.setDirty();
    // Update permissions to videos
    if (that.cdsDepositCtrl.depositType === 'project') {
      $scope.$emit(
        'cds.deposit.project.permissions.update', that.cdsDepositCtrl.record._access, that.permissions
      );
    }
  }

  // Listen for permission/access rights change
  $scope.$on('cds.deposit.video.permissions.update', function(evt, _access, permissions) {
    var ctrl = that.cdsDepositCtrl;
    if (ctrl.depositType === 'video') {
      ctrl.record._access = angular.copy(
        _access || {}
      );
      // Update also the model
      that.selectedRestricted = ctrl.record._access.read;
      // Set the permissions
      that.permissions = angular.copy(permissions);
      // Set the form dirty
      ctrl.setDirty();
    }
  });

  function makeActionWithPreAndPost(actionName) {
    var ctrl = that.cdsDepositCtrl;
    ctrl.preActions();
    return ctrl.makeSingleAction(actionName)
      .then(ctrl.onSuccessAction, ctrl.onErrorAction)
      .finally(ctrl.postActions);
  }

  this.deleteDeposit = function () {
    $scope.$broadcast('cds.deposit.delete');
  }
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
