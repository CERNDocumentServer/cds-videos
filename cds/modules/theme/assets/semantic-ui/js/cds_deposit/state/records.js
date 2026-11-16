/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Pure helpers on the deposit records: they never change their arguments. */

import _cloneDeep from "lodash/cloneDeep";
import _find from "lodash/find";
import _groupBy from "lodash/groupBy";
import _isEmpty from "lodash/isEmpty";
import _omit from "lodash/omit";
import _pick from "lodash/pick";
import _toPath from "lodash/toPath";

import {
  DEPOSIT_EXTRACTED_METADATA,
  DEPOSIT_STATES,
  DEPOSIT_STATUSES,
  INHERITED_PROPERTIES,
  urlBuilder,
} from "../constants";

/** Fields edited by the forms of each deposit type. */
export const FORM_FIELDS = {
  project: [
    "title",
    "description",
    "keywords",
    "_eos_library_path",
    "category",
    "type",
    "contributors",
    "license",
    "translations",
  ],
  video: [
    "title",
    "description",
    "keywords",
    "language",
    "date",
    "contributors",
    "featured",
    "vr",
    "license",
    "copyright",
    "translations",
    "related_links",
    "related_identifiers",
  ],
};

/**
 * Copy of ``object`` with ``value`` at ``path``. Only the objects along the
 * path are copied, the others are shared.
 */
export function setIn(object, path, value) {
  const [key, ...rest] = Array.isArray(path) ? path : _toPath(path);
  const current = object === null || object === undefined ? undefined : object;
  const next = rest.length
    ? setIn(current === undefined ? undefined : current[key], rest, value)
    : value;
  if (Array.isArray(current) || (current === undefined && /^\d+$/.test(key))) {
    const copy = current ? [...current] : [];
    copy[key] = next;
    return copy;
  }
  return { ...(current || {}), [key]: next };
}

/** Copy of ``object`` without the property at ``path``. */
export function unsetIn(object, path) {
  const [key, ...rest] = Array.isArray(path) ? path : _toPath(path);
  if (object === null || typeof object !== "object" || !(key in object)) {
    return object;
  }
  if (rest.length) {
    return { ...object, [key]: unsetIn(object[key], rest) };
  }
  return _omit(object, key);
}

/* Status */

export function isPublished(record) {
  return record._deposit.status === "published";
}

export function isDraft(record) {
  return record._deposit.status === "draft";
}

export function findMasterFile(record) {
  return _find(record._files, { context_type: "master" });
}

/** State of the tasks of a deposit (``_cds.state``). */
export function taskStates(record) {
  return (record._cds && record._cds.state) || {};
}

export function anyTaskIsRunning(record) {
  const states = taskStates(record);
  return Object.keys(states).some((key) =>
    ["PENDING", "STARTED"].includes(states[key])
  );
}

/** The running task and the overall status of the tasks of a deposit. */
export function depositStatus(record) {
  const states = taskStates(record);
  const startedTask =
    DEPOSIT_STATES.find((task) => states[task] === "STARTED") || null;
  const values = Object.values(
    _omit(states, "file_video_extract_chapter_frames")
  );
  let status;
  if (!values.length) {
    status = null;
  } else if (values.includes(DEPOSIT_STATUSES.FAILURE)) {
    status = DEPOSIT_STATUSES.FAILURE;
  } else if (values.includes(DEPOSIT_STATUSES.STARTED)) {
    status = DEPOSIT_STATUSES.STARTED;
  } else if (values.includes(DEPOSIT_STATUSES.PENDING)) {
    status = DEPOSIT_STATUSES.PENDING;
  } else {
    status = DEPOSIT_STATUSES.SUCCESS;
  }
  return { startedTask, status };
}

/** URL of the video player, once a subformat is ready. */
export function previewerUrl(record) {
  const master = findMasterFile(record);
  if (master && master.subformat) {
    const finished = master.subformat.find(
      (fmt) => fmt.completed && !_isEmpty(fmt.checksum)
    );
    if (finished) {
      return urlBuilder.video({
        deposit: record._deposit.id,
        key: finished.key,
      });
    }
  }
  return null;
}

/* Records of the form */

/** Default values of the JSON schemas, as the form set them before. */
export function applySchemaDefaults(record, type, showAvcRestrictedFields) {
  let result = record;
  if (type === "video") {
    const defaults = { language: "en", vr: false };
    // The checkboxes of angular-schema-form defaulted to ``false``
    if (showAvcRestrictedFields === true) {
      defaults.featured = false;
    }
    Object.entries(defaults).forEach(([key, value]) => {
      if (result[key] === undefined) {
        result = { ...result, [key]: value };
      }
    });
  }
  const translations = result.translations || [];
  if (translations.some((item) => item && item.language === undefined)) {
    result = {
      ...result,
      translations: translations.map((item) =>
        item && item.language === undefined ? { ...item, language: "en" } : item
      ),
    };
  }
  return result;
}

/** Values of the form fields of a record. */
export function formValues(record, type) {
  return _cloneDeep(_pick(record, FORM_FIELDS[type]));
}

function hasNoProperties(object) {
  return (
    object !== null &&
    typeof object === "object" &&
    Object.getOwnPropertyNames(object).length === 0
  );
}

function getPath(object, path) {
  return _toPath(path).reduce(
    (value, part) => (value ? value[part] : undefined),
    object
  );
}

/**
 * Copy of a video record with the metadata of its project: the missing
 * values, or all of them with ``force``.
 */
export function inheritMetadata(record, project, force) {
  return INHERITED_PROPERTIES.reduce((result, path) => {
    const inherited = getPath(project, path);
    const own = getPath(result, path);
    if (inherited && (!own || force === true)) {
      return setIn(result, path, _cloneDeep(inherited));
    }
    if (Array.isArray(own) && own.every(hasNoProperties)) {
      return setIn(result, path, _cloneDeep(inherited));
    }
    return result;
  }, record);
}

/** Missing ``keywords`` of a project and its videos (not added or saved). */
export function withKeywords(metadata) {
  return {
    ...metadata,
    keywords: metadata.keywords || [],
    videos: (metadata.videos || []).map((video) =>
      video.keywords ? video : { ...video, keywords: [] }
    ),
  };
}

/**
 * Metadata extracted from the video file which can fill the form: the
 * values for the record and the values to display, or ``false``.
 */
export function extractedMetadataToFill(allMetadata) {
  if (!allMetadata) {
    return false;
  }
  const toFill = {};
  const toDisplay = {};
  Object.keys(DEPOSIT_EXTRACTED_METADATA).forEach((item) => {
    const value = DEPOSIT_EXTRACTED_METADATA[item](toFill, allMetadata);
    if (value) {
      toDisplay[item] = value;
    }
  });
  return _isEmpty(toFill) ? false : [toFill, toDisplay];
}

/** Subformats of the master file from the transcoding tasks. */
export function transcodingSubformats(tasks) {
  const flags = {
    SUCCESS: "status_completed",
    FAILURE: "status_failure",
    PENDING: "status_pending",
    STARTED: "status_started",
    CANCELLED: "status_cancelled",
  };
  return (_groupBy(tasks, "name").file_transcode || [])
    .filter((task) => task.info)
    .map((task) => {
      const flag = flags[task.status];
      return flag ? { ...task.info.payload, [flag]: true } : task.info.payload;
    });
}

/* Files */

export function extractBasename(key) {
  return key.slice(0, key.lastIndexOf("."));
}

/** Basename of a video file, or ``null``. */
export function videoBasename(key, extensions) {
  const lower = key.toLowerCase();
  const match = (extensions || "mp4,mkv,mov")
    .split(",")
    .some((ext) => lower.endsWith(ext.toLowerCase()));
  return match ? extractBasename(key) : null;
}

/**
 * Separate the video files (by basename) and their related files (same
 * basename prefix) from the files of the project.
 */
export function filterOutFiles(files, extensions) {
  const videos = {};
  const videoFiles = {};
  const others = [];
  files.forEach((file) => {
    const basename = videoBasename(file.key, extensions);
    if (basename !== null) {
      videos[basename] = file;
      videoFiles[basename] = [];
    } else {
      others.push(file);
    }
  });
  const project = [];
  others.forEach((file) => {
    const basename = extractBasename(file.key);
    const videoMatch = Object.keys(videos).find((key) =>
      basename.startsWith(key)
    );
    const target = videoMatch ? videoFiles[basename] : project;
    if (target) {
      target.push(file);
    }
  });
  return { project, videos, videoFiles };
}
