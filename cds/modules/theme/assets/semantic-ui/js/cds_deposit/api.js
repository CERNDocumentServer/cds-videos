/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/*
 * REST API of the deposit (the former ``cdsAPI`` factory and
 * ``depositActions`` provider).
 */

import _cloneDeep from "lodash/cloneDeep";
import _isArray from "lodash/isArray";
import _isEmpty from "lodash/isEmpty";
import _isEqual from "lodash/isEqual";
import _isObject from "lodash/isObject";
import _mapValues from "lodash/mapValues";
import _omitBy from "lodash/omitBy";

import { http } from "@js/cds/api";

import { urlBuilder } from "./constants";

function isPopulated(val) {
  return (
    val !== null &&
    val !== undefined &&
    !_isEqual(val, "") &&
    !_isEqual(val, []) &&
    !(val.constructor === Object && _isEmpty(val))
  );
}

function noPayload() {
  return null;
}

/** Remove the empty values of the payload, recursively. */
export function sanitizeData(payload) {
  if (_isArray(payload)) {
    return payload.map(sanitizeData).filter(isPopulated);
  } else if (_isObject(payload)) {
    return _omitBy(_mapValues(payload, sanitizeData), (o) => !isPopulated(o));
  }
  return payload;
}

function actionsFor(depositType) {
  const mimetype = `application/vnd.${depositType}.partial+json`;
  return {
    CREATE: {
      method: "POST",
      link: "self",
      headers: { "Content-Type": mimetype, Accept: mimetype },
      preprocess: sanitizeData,
    },
    SAVE_PARTIAL: {
      method: "PUT",
      link: "self",
      headers: { "Content-Type": mimetype, Accept: mimetype },
      preprocess: sanitizeData,
    },
    SAVE: { method: "PUT", link: "self", preprocess: sanitizeData },
    EDIT: { method: "POST", link: "edit", preprocess: noPayload },
    PUBLISH: { method: "POST", link: "publish", preprocess: noPayload },
    DELETE: { method: "DELETE", link: "self" },
    BUCKET: { method: "GET", link: "bucket" },
  };
}

/** ``depositActions``: the actions of each deposit type. */
export const DEPOSIT_ACTIONS = {
  project: actionsFor("project"),
  video: actionsFor("video"),
};

/** Normalize an axios error to the response object of AngularJS ``$http``. */
function toResponse(error) {
  if (error && error.response) {
    return error.response;
  }
  return { data: {}, status: 0, error };
}

/**
 * Make a request, resolving and rejecting with the response. ``options``
 * are extra request options, like ``ignoreLoadingBar``.
 */
export function action(url, method, payload, headers, options) {
  const config = {
    ...(options || {}),
    url,
    method,
    headers: { "Content-Type": "application/json", ...(headers || {}) },
  };
  if (payload !== undefined && payload !== null && method !== "GET") {
    config.data = payload;
  }
  return http.request(config).then(
    (response) => response,
    (error) => Promise.reject(toResponse(error))
  );
}

/**
 * Run functions returning promises one after the other. Each item is a
 * function, or ``[function, callback]`` with a callback of its response.
 */
export function chainedActions(promises) {
  const queue = [...promises];
  const data = [];
  return new Promise((resolve, reject) => {
    function next() {
      if (queue.length === 0) {
        resolve(data);
        return;
      }
      let fn = queue.shift();
      let callback;
      if (typeof fn !== "function") {
        callback = fn[1];
        fn = fn[0];
      }
      fn().then(
        (response) => {
          data.push(response);
          if (typeof callback === "function") {
            callback(response);
          }
          next();
        },
        (error) => reject(error)
      );
    }
    next();
  });
}

/** Copy of the data without the files and the empty values. */
export function cleanData(data, unwanted) {
  const unwantedValues = unwanted || [[null], [undefined]];
  const result = _cloneDeep(data);
  delete result._files;
  Object.keys(result).forEach((key) => {
    unwantedValues.forEach((value) => {
      if (_isEqual(value, result[key])) {
        delete result[key];
      }
    });
  });
  return result;
}

export function getUrlPath(url) {
  const parser = document.createElement("a");
  parser.href = url;
  return parser.pathname;
}

export function resolveJSON(url) {
  return http
    .get(url, {
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        Pragma: "no-cache",
        Expires: 0,
      },
    })
    .then(
      (response) => response,
      (error) => Promise.reject(toResponse(error))
    );
}

function containsLink(links, link) {
  return links && Object.keys(links).indexOf(link) > -1;
}

/** URL of an action of a deposit. */
export function guessEndpoint(record, depositType, actionName, links) {
  const link = DEPOSIT_ACTIONS[depositType][actionName].link;
  const isMaster = depositType === "project";
  if (containsLink(links, link)) {
    return links[link];
  }
  if (!isMaster) {
    if (link === "self") {
      return urlBuilder.selfVideo({ deposit: record._deposit.id });
    } else if (link === "bucket") {
      return urlBuilder.bucketVideo({ bucket: record._buckets.deposit });
    }
    return urlBuilder.actionVideo({
      deposit: record._deposit.id,
      action: actionName.toLowerCase(),
    });
  }
  return undefined;
}

export function makeAction(url, depositType, actionName, payload) {
  const actionInfo = DEPOSIT_ACTIONS[depositType][actionName];
  let data = payload;
  if (actionInfo.preprocess) {
    data = actionInfo.preprocess(payload);
  }
  return action(url, actionInfo.method, data, actionInfo.headers);
}
