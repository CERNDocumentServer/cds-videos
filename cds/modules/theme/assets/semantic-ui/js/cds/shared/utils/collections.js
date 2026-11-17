/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Filter, find and group lists of objects. */

import _filter from "lodash/filter";
import _get from "lodash/get";
import _groupBy from "lodash/groupBy";
import _isEmpty from "lodash/isEmpty";
import _matchesProperty from "lodash/matchesProperty";

/** Group items by a (deep) field, keeping the insertion order of groups. */
export function groupBy(items, field, defaultGroup) {
  return _groupBy(items, (e) => _get(e, field) || defaultGroup);
}

export function findBy(data, key, value) {
  if (!_isEmpty(data)) {
    return _filter(data, _matchesProperty(key, value));
  }
  return undefined;
}

/**
 * AngularJS ``filter`` filter with a string expression: keep the items that
 * have any (deep) property containing the expression, case insensitive.
 */
export function filterByText(items, expression) {
  if (!expression) {
    return items || [];
  }
  const needle = String(expression).toLowerCase();
  function matches(value) {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === "object") {
      return Object.keys(value).some(
        (key) => key.charAt(0) !== "$" && matches(value[key])
      );
    }
    return String(value).toLowerCase().indexOf(needle) > -1;
  }
  return (items || []).filter(matches);
}

/** Return the value of a lodash path in an object, or a default. */
export const get = _get;

/**
 * AngularJS ``filter`` filter with an object expression, for example
 * ``filter:{context_type:'subtitle', content_type:'vtt'}``: every property of
 * the pattern must be contained (case insensitive) in the item property.
 */
export function filterByFields(items, pattern) {
  const keys = Object.keys(pattern || {});
  return (items || []).filter((item) =>
    keys.every((key) => {
      const expected = pattern[key];
      if (expected === undefined || expected === null || expected === "") {
        return true;
      }
      if (item === null || item === undefined) {
        return false;
      }
      const actual = item[key];
      if (actual === undefined || actual === null) {
        return false;
      }
      if (typeof actual === "object") {
        return filterByText([actual], expected).length > 0;
      }
      return (
        String(actual).toLowerCase().indexOf(String(expected).toLowerCase()) >
        -1
      );
    })
  );
}

export const isEmpty = _isEmpty;
