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
 * Requests to the REST API of the deposits.
 */

import _cloneDeep from "lodash/cloneDeep";
import _isArray from "lodash/isArray";
import _isEmpty from "lodash/isEmpty";
import _isEqual from "lodash/isEqual";
import _isObject from "lodash/isObject";
import _mapValues from "lodash/mapValues";
import _omitBy from "lodash/omitBy";

import { http } from "@js/cds/shared/api";

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
export async function action(url, method, payload, headers, options) {
  const config = {
    ...(options || {}),
    url,
    method,
    headers: { "Content-Type": "application/json", ...(headers || {}) },
  };
  if (payload !== undefined && payload !== null && method !== "GET") {
    config.data = payload;
  }
  try {
    return await http.request(config);
  } catch (error) {
    throw toResponse(error);
  }
}

/** Run functions returning promises one after the other. */
export async function chainedActions(promises) {
  const data = [];
  for (const fn of promises) {
    data.push(await fn());
  }
  return data;
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

/**
 * Headers bypassing the browser cache. The deposit API answers 304 as long as
 * the revision of the record is the same, while the task states it returns
 * come from the workflows and change without a new revision.
 */
export const NO_CACHE_HEADERS = {
  "Cache-Control": "no-cache, no-store, must-revalidate",
  Pragma: "no-cache",
  Expires: 0,
};

export async function resolveJSON(url) {
  try {
    return await http.get(url, { headers: NO_CACHE_HEADERS });
  } catch (error) {
    throw toResponse(error);
  }
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
