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
 * Validation of the deposit forms: the required fields of the JSON schemas
 * and of the form definitions, with the same messages as the previous
 * interface.
 */

import { setIn } from "formik";
import _get from "lodash/get";

const REQUIRED = "Required";

function isEmptyValue(value) {
  return value === undefined || value === null || value === "";
}

function required(errors, values, path) {
  return isEmptyValue(_get(values, path))
    ? setIn(errors, path, REQUIRED)
    : errors;
}

function minItems(errors, values, path) {
  const value = _get(values, path);
  if (!Array.isArray(value)) {
    return setIn(errors, path, REQUIRED);
  }
  if (value.length < 1) {
    return setIn(
      errors,
      path,
      `Array is too short (${value.length}), minimum 1`
    );
  }
  return errors;
}

function contributors(errors, values) {
  let result = minItems(errors, values, "contributors");
  (values.contributors || []).forEach((contributor, index) => {
    if (!contributor || isEmptyValue(contributor.name)) {
      result = setIn(result, `contributors.${index}.name`, REQUIRED);
    }
    if (!contributor || isEmptyValue(contributor.role)) {
      result = setIn(result, `contributors.${index}.role`, REQUIRED);
    }
  });
  return result;
}

export function validateProject(values) {
  let errors = {};
  errors = required(errors, values, "title.title");
  errors = required(errors, values, "description");
  errors = required(errors, values, "category");
  errors = required(errors, values, "type");
  errors = contributors(errors, values);
  return errors;
}

export function validateVideo(values) {
  let errors = {};
  errors = required(errors, values, "title.title");
  errors = required(errors, values, "description");
  errors = required(errors, values, "date");
  errors = required(errors, values, "language");
  errors = contributors(errors, values);
  if (isEmptyValue(values.copyright)) {
    errors = setIn(errors, "copyright", REQUIRED);
  }
  if (!Array.isArray(values.license)) {
    errors = setIn(errors, "license", REQUIRED);
  }
  (values.related_identifiers || []).forEach((identifier, index) => {
    ["identifier", "scheme", "relation_type"].forEach((key) => {
      if (!identifier || isEmptyValue(identifier[key])) {
        errors = setIn(errors, `related_identifiers.${index}.${key}`, REQUIRED);
      }
    });
  });
  return errors;
}
