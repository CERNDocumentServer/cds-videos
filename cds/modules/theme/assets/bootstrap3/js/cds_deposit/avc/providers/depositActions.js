import angular from "angular";
import _ from "lodash";

export function getCookie(cname) {
  let name = cname + "=";
  let decodedCookie = decodeURIComponent(document.cookie);
  let ca = decodedCookie.split(";");
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == " ") {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}

function depositActions() {
  var actions = {};

  return {
    setValues: function (depositTypes, extraActions) {
      actions = depositTypes.reduce(function (obj, depositType) {
        var mimetype = "application/vnd." + depositType + ".partial+json";
        obj[depositType] = Object.assign(
          {
            CREATE: {
              method: "POST",
              link: "self",
              headers: {
                "Content-Type": mimetype,
                Accept: mimetype,
                "X-CSRFToken": getCookie("csrftoken"),
              },
              preprocess: sanitizeData,
            },
            SAVE_PARTIAL: {
              method: "PUT",
              link: "self",
              headers: {
                "Content-Type": mimetype,
                Accept: mimetype,
                "X-CSRFToken": getCookie("csrftoken"),
              },
              preprocess: sanitizeData,
            },
            SAVE: {
              method: "PUT",
              link: "self",
              preprocess: sanitizeData,
              headers: {
                "X-CSRFToken": getCookie("csrftoken"),
              },
            },
            EDIT: {
              method: "POST",
              link: "edit",
              preprocess: noPayload,
              headers: {
                "X-CSRFToken": getCookie("csrftoken"),
              },
            },
            PUBLISH: {
              method: "POST",
              link: "publish",
              preprocess: noPayload,
              headers: {
                "X-CSRFToken": getCookie("csrftoken"),
              },
            },
            DELETE: {
              method: "DELETE",
              link: "self",
              headers: {
                "X-CSRFToken": getCookie("csrftoken"),
              },
            },
            BUCKET: {
              method: "GET",
              link: "bucket",
            },
          },
          extraActions || {}
        );
        return obj;
      }, {});
    },
    $get: function () {
      return actions;
    },
  };
}

function isPopulated(val) {
  return (
    val !== null &&
    val !== undefined &&
    !_.isEqual(val, "") &&
    !_.isEqual(val, []) &&
    !(val.constructor === Object && _.isEmpty(val))
  );
}

function noPayload(payload) {
  return null;
}

function sanitizeData(payload) {
  if (_.isArray(payload)) {
    return payload.map(sanitizeData).filter(isPopulated);
  } else if (_.isObject(payload)) {
    return _.chain(payload)
      .mapValues(sanitizeData)
      .omitBy(function (o) {
        return !isPopulated(o);
      })
      .value();
  } else {
    return payload;
  }
}

angular
  .module("cdsDeposit.providers")
  .provider("depositActions", depositActions);
