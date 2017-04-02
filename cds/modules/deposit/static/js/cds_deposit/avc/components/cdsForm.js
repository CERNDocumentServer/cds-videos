function cdsFormCtrl($scope, $http, $q, schemaFormDecorators) {

  var that = this;
  this.$onInit = function() {
    this.cdsDepositCtrl.depositForm = {};
    this.cdsDepositCtrl.cdsDepositsCtrl.JSONResolver(this.form)
    .then(function(response) {
      that.form = response.data;
    });

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

  this.autocompleteLicenses = function(options, query) {
    if (query) {
      // Parse the url parameters
      return $http.get(options.url, {
        params: {"text": query}
      }).then(function(data) {
        that.lastLicenseSuggestions = {
          data: data.data['text'][0]['options'].map(function(license) {
            var value = license['payload'].id;
            var text = value;

            return {
              text: text,
              value: value
            };
          }).slice(0, 20)
        };
        return that.lastLicenseSuggestions;
      });
    } else {
      // If the query string is empty and there's already a value set on the
      // model, this means that the form was just loaded and is trying to
      // display this value.
      // This also happens when the user clicks on a suggestion or on the
      // suggestion field. In this case, return the previous suggestions.
      var defer = $q.defer();
      defer.resolve(
        that.lastLicenseSuggestions ||
        {
          data: _.map(
            that.cdsDepositCtrl.record.license || [],
            function(_license) {
              return {
                text: _license.license, value: _license.license
              }
            }
          )
        }
      );
      return defer.promise;
    }
  };

  this.autocompleteAuthors = function(options, query) {
    if (query) {
      // Parse the url parameters
      return $http.get(options.url, {
        params: angular.merge({
          query: query
        }, options.extraParams)
      }).then(function(data) {
        that.lastAuthorSuggestions = {
          data: data.data.map(function (author) {
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

            return {
              text: fullName,
              value: valueObj
            };
          }).slice(0, 20)
        };
        return that.lastAuthorSuggestions;
      });
    } else {
      // If the query string is empty and there's already a value set on the
      // model, this means that the form was just loaded and is trying to
      // display this value.
      // This also happens when the user clicks on a suggestion or on the
      // suggestion field. In this case, return the previous suggestions.
      var defer = $q.defer();
      defer.resolve(
        that.lastAuthorSuggestions ||
        {
          data: _.map(
            that.cdsDepositCtrl.record.contributors || [],
            function(_contributor) {
              return {
                text: _contributor.name, value: _contributor
              }
            }
          )
        }
      );
      return defer.promise;
    }
  };

  this.types = $q.defer();

  this.autocompleteKeywords = function(options, query) {
    if (query) {
      // Parse the url parameters
      return $http.get(options.url, {
        params: {
          "suggest-name": query
        }
      }).then(function(data) {
        that.lastKeywordSuggestions = {
          data: data.data['suggest-name'][0]['options'].concat(that.cdsDepositCtrl.record.keywords || []).map(function(keyword) {
            var name = (keyword.payload) ? keyword.payload.name : keyword.name;
            var key_id = (keyword.payload) ? keyword.payload.key_id : keyword.key_id;
            return {
              name: name,
              value: {
                name: name,
                key_id: key_id
              }
            };
          }).slice(0, 20)
        };

        return that.lastKeywordSuggestions;
        return { data : angular.merge(
          {},
          that.lastKeywordSuggestions.data,
          _.map(
            that.cdsDepositCtrl.record.keywords || [],
            function(_keyword) {
              return {
                name: _keyword.name, value: _keyword,
              }
            })
        )}
      });
    } else {
      // If the query string is empty and there's already a value set on the
      // model, this means that the form was just loaded and is trying to
      // display this value.
      // This also happens when the user clicks on a suggestion or on the
      // suggestion field. In this case, return the previous suggestions.
      var defer = $q.defer();
      defer.resolve(
        that.lastKeywordSuggestions || {data:  _.map(
          that.cdsDepositCtrl.record.keywords || [],
          function(_keyword) {
            return {
              name: _keyword.name, value: _keyword
            }
          })}
      );
      return defer.promise;
    }
  };

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
