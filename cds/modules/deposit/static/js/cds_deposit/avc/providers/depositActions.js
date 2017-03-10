function depositActions() {
  var actions = {};
  return {
    setValues: function(depositTypes, extraActions) {
      actions = depositTypes.reduce(function(obj, depositType) {
        obj[depositType] = Object.assign({
          CREATE: {
            method: 'POST',
            link: 'self',
            mimetype: 'application/vnd.' + depositType + '.partial+json',
            preprocess: sanitizeData
          },
          SAVE_PARTIAL: {
            method: 'PUT',
            link: 'self',
            mimetype: 'application/vnd.' + depositType + '.partial+json',
            preprocess: sanitizeData
          },
          SAVE: {
            method: 'PUT',
            link: 'self'
          },
          EDIT: {
            method: 'POST',
            link: 'edit'
          },
          PUBLISH: {
            method: 'POST',
            link: 'publish'
          },
          DELETE: {
            method: 'DELETE',
            link: 'self'
          }
        }, extraActions || {})
        return obj
      }, {})
    },
    $get: function() {
      return actions;
    }
  };
}

function isPopulated(val) {
  return val !== null && val !== undefined &&
    !(val.constructor === Object && _.isEmpty(val));
}

function sanitizeData(payload) {
    if (_.isArray(payload)) {
      return payload.map(sanitizeData).filter(isPopulated);
    } else if (_.isObject(payload)) {
      return _.chain(payload)
              .mapObject(sanitizeData)
              .omit(function(value) {
                return !isPopulated(value);
              })
              .value();
    } else {
      return payload;
    }
}

angular.module('cdsDeposit.providers')
  .provider('depositActions', depositActions);
