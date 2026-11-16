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
 * Search parameters in the format used by CDS since the AngularJS interface
 * (invenio-search-js), and their conversion to and from the react-searchkit
 * query state.
 *
 * The parameters are a flat object, e.g.
 * ``{page: 1, size: 21, q: "atlas", sort: "mostrecent", collections: ["A"]}``:
 * ``q``, ``sort``, ``page`` and ``size`` are the query string, the sorting
 * and the pagination, and every other key is a filter (facets, years range).
 * They are used as they are in the page URL and in the REST API requests, so
 * the existing links and bookmarks keep working.
 */

import _isEqual from "lodash/isEqual";

export const RESERVED_PARAMS = ["q", "sort", "page", "size"];

/** Default parameters of invenio-search-js. */
export const DEFAULT_PARAMS = { page: 1, size: 20 };

/**
 * Parse a query string like AngularJS ``$location.search()``: ``+`` are
 * spaces, repeated keys are arrays and keys without a value are ``true``.
 */
export function parseLocationSearch(search) {
  const result = {};
  (search || "")
    .replace(/^\?/, "")
    .split("&")
    .forEach((keyValue) => {
      if (!keyValue) return;
      const parts = keyValue.replace(/\+/g, "%20").split("=");
      let key;
      try {
        key = decodeURIComponent(parts[0]);
      } catch (e) {
        return;
      }
      if (key === undefined || key === "") return;
      let value = true;
      if (parts.length > 1) {
        try {
          value = decodeURIComponent(parts.slice(1).join("="));
        } catch (e) {
          return;
        }
      }
      if (!Object.prototype.hasOwnProperty.call(result, key)) {
        result[key] = value;
      } else if (Array.isArray(result[key])) {
        result[key].push(value);
      } else {
        result[key] = [result[key], value];
      }
    });
  return result;
}

/** Encode a query string component like AngularJS ``encodeUriQuery``. */
function encodeUriQuery(value) {
  return encodeURIComponent(value)
    .replace(/%40/gi, "@")
    .replace(/%3A/gi, ":")
    .replace(/%24/g, "$")
    .replace(/%2C/gi, ",")
    .replace(/%3B/gi, ";");
}

/** Serialize parameters like AngularJS ``$location.search(object)``. */
export function toLocationSearch(params) {
  const parts = [];
  Object.keys(params || {}).forEach((key) => {
    const value = params[key];
    if (value === undefined || value === null) return;
    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      parts.push(
        encodeUriQuery(key) + (item === true ? "" : "=" + encodeUriQuery(item))
      );
    });
  });
  return parts.length ? "?" + parts.join("&") : "";
}

/** Serialize the parameters of a REST API request (repeated keys). */
export function toRequestParams(params) {
  const output = [];
  Object.keys(params || {}).forEach((key) => {
    const value = params[key];
    if (value === undefined || value === null) return;
    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      output.push(encodeURIComponent(key) + "=" + encodeURIComponent(item));
    });
  });
  return output.join("&");
}

/** Parse the query string of an URL, without arrays (``links.self``). */
export function parseURLQueryString(url) {
  const queryString = ((url || "").split("?")[1] || "").split("&");
  const data = {};
  for (let i = 0; i < queryString.length; i += 1) {
    const param = (queryString[i] || "").split("=");
    const key = decodeURIComponent(param[0] || "");
    if (key) {
      data[key] = decodeURIComponent(param[1] || "");
    }
  }
  return data;
}

function toInt(value, fallback) {
  const result = parseInt(value, 10);
  return isNaN(result) ? fallback : result;
}

/** Filters (``[[key, value], ...]``) of a parameters object. */
function paramsToFilters(params) {
  const filters = [];
  Object.keys(params || {})
    .filter((key) => RESERVED_PARAMS.indexOf(key) === -1)
    .forEach((key) => {
      const value = params[key];
      const values = Array.isArray(value) ? value : [value];
      values
        .filter((item) => item !== undefined && item !== null)
        .forEach((item) =>
          filters.push([key, item === true ? "" : String(item)])
        );
    });
  return filters;
}

/** Group a list of filters by key: one value or an array per key. */
function filtersToParams(filters, params) {
  (filters || []).forEach(([key, value]) => {
    if (!Object.prototype.hasOwnProperty.call(params, key)) {
      params[key] = value;
    } else if (Array.isArray(params[key])) {
      params[key].push(value);
    } else {
      params[key] = [params[key], value];
    }
  });
  return params;
}

/** Convert parameters to a react-searchkit query state. */
export function paramsToQueryState(params, hiddenParams = {}) {
  const q = params.q;
  const sort = params.sort;
  return {
    queryString: q === undefined || q === null || q === true ? "" : String(q),
    sortBy:
      sort === undefined || sort === null || sort === "" ? null : String(sort),
    sortOrder: null,
    page: toInt(params.page, -1),
    size: toInt(params.size, -1),
    filters: paramsToFilters(params),
    hiddenParams: paramsToFilters(hiddenParams),
  };
}

/**
 * Convert a react-searchkit query state to parameters, in the order of
 * ``keyOrder`` (the keys of the previous parameters) and then new keys.
 */
export function queryStateToParams(queryState, keyOrder = []) {
  const params = {};
  if (queryState.page > 0) params.page = queryState.page;
  if (queryState.size > 0) params.size = queryState.size;
  if (queryState.queryString) params.q = queryState.queryString;
  if (queryState.sortBy) params.sort = queryState.sortBy;
  filtersToParams(queryState.filters, params);
  const ordered = {};
  keyOrder
    .filter((key) => Object.prototype.hasOwnProperty.call(params, key))
    .forEach((key) => {
      ordered[key] = params[key];
    });
  Object.keys(params).forEach((key) => {
    if (!Object.prototype.hasOwnProperty.call(ordered, key)) {
      ordered[key] = params[key];
    }
  });
  return ordered;
}

/** Hidden parameters of a query state (sent to the server only). */
export function hiddenParamsOf(queryState) {
  return filtersToParams(queryState.hiddenParams, {});
}

/**
 * New parameters after a change, with the rule of invenio-search-js: when
 * the page is not changed, any other change brings back to the first page.
 */
export function changedParams(current, changes) {
  const next = { ...current, ...changes };
  if (_isEqual(next, current)) {
    return null;
  }
  if (String(current.page) === String(next.page)) {
    next.page = 1;
  }
  return next;
}
