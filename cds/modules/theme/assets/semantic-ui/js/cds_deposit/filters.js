/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Filters of the former ``cdsDeposit.filters`` module. */

import _get from "lodash/get";
import _includes from "lodash/includes";
import _omit from "lodash/omit";
import _values from "lodash/values";

import {
  DEPOSIT_STATES,
  DEPOSIT_STATUSES,
  TASK_REPRESENTATIONS,
} from "./constants";

/** Tasks in the order of ``DEPOSIT_STATES`` (only the main ones). */
export function orderTasks(input) {
  const ordered = [];
  if (input) {
    DEPOSIT_STATES.forEach((task) => {
      if (Object.prototype.hasOwnProperty.call(input, task)) {
        ordered.push([task, input[task]]);
      }
    });
  }
  return ordered;
}

export function overallState(tasks) {
  const values = _values(_omit(tasks, "file_video_extract_chapter_frames"));
  if (values.length !== 0) {
    if (_includes(values, "FAILURE")) {
      return DEPOSIT_STATUSES.FAILURE;
    } else if (_includes(values, "STARTED")) {
      return DEPOSIT_STATUSES.STARTED;
    } else if (values.every((val) => val === "SUCCESS")) {
      return DEPOSIT_STATUSES.SUCCESS;
    }
  }
  return DEPOSIT_STATUSES.PENDING;
}

export function progressClass(input) {
  switch (input) {
    case "SUCCESS":
      return "text-success";
    case "STARTED":
      return "text-warning";
    case "FAILURE":
      return "text-danger";
    case "PENDING":
    case "CANCELLED":
      return "text-muted";
    default:
      return "";
  }
}

export function progressIcon(input) {
  switch (input) {
    case "SUCCESS":
      return "fa-check";
    case "PENDING":
    case "STARTED":
      return "fa-spinner fa-spin";
    case "FAILURE":
      return "fa-times";
    default:
      return "";
  }
}

export function taskRepr(input) {
  return TASK_REPRESENTATIONS[input] || input;
}

/** Display value of an autocomplete item (``parseAutocomplete``). */
export function parseAutocomplete(input, key) {
  if (input !== null && typeof input === "object") {
    return _get(input, key || "name");
  }
  return input;
}

export function toInt(input) {
  const result = parseInt(input, 10);
  return isNaN(result) ? input : result;
}
