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
 * State of the deposit page: the static configuration, the page (project,
 * order of the videos, categories) and one entry per deposit, keyed by its
 * id. The project entry has no ``videos``: they are the video entries.
 */

import _cloneDeep from "lodash/cloneDeep";
import _merge from "lodash/merge";
import _omit from "lodash/omit";
import _toPath from "lodash/toPath";

import { applySchemaDefaults, isPublished, setIn, taskStates } from "./records";

export const ActionTypes = {
  PROJECT_SET: "deposit/PROJECT_SET",
  PERMISSION_DENIED: "deposit/PERMISSION_DENIED",
  CATEGORIES_LOADED: "deposit/CATEGORIES_LOADED",
  VIDEO_ADDED: "deposit/VIDEO_ADDED",
  VIDEO_REMOVED: "deposit/VIDEO_REMOVED",
  DUPLICATE_VIDEOS: "deposit/DUPLICATE_VIDEOS",
  ACTION_STARTED: "deposit/ACTION_STARTED",
  ACTION_FINISHED: "deposit/ACTION_FINISHED",
  DEPOSIT_PATCHED: "deposit/DEPOSIT_PATCHED",
  RECORD_REPLACED: "deposit/RECORD_REPLACED",
  RECORD_MERGED: "deposit/RECORD_MERGED",
  RECORD_VALUE_SET: "deposit/RECORD_VALUE_SET",
  FILES_REFRESHED: "deposit/FILES_REFRESHED",
  FILES_CHANGED: "deposit/FILES_CHANGED",
  TASK_STATE_SET: "deposit/TASK_STATE_SET",
  PRISTINE: "deposit/PRISTINE",
  FORM_ERRORS_SET: "deposit/FORM_ERRORS_SET",
  BACKEND_ERROR_ADDED: "deposit/BACKEND_ERROR_ADDED",
  BACKEND_ERROR_REMOVED: "deposit/BACKEND_ERROR_REMOVED",
};

/** Entry of a deposit (``type`` is ``project`` or ``video``). */
function newDeposit(type, record, links, config) {
  return {
    id: record._deposit.id,
    type,
    record: applySchemaDefaults(record, type, config.showAvcRestrictedFields),
    links,
    // Requests of the action buttons (save, publish, ...) in progress
    pending: 0,
    alerts: [],
    dirty: false,
    formErrors: {},
    backendErrors: {},
    // Counters: the form takes the values of the record (``sync``) or is
    // reset to them (``reset``) when they change
    formSync: 0,
    formReset: 0,
    // The details of a published deposit are hidden
    showAll: !isPublished(record),
    permissions: undefined,
    metadataToFill: false,
    previewer: null,
    framesReady: taskStates(record).file_video_extract_frames === "SUCCESS",
    waitingUpload: false,
    presets: [],
    // Tasks of the video workflow
    tasksByName: {},
    tasksById: {},
    stateReporter: {},
    // Uploads of the deposit
    uploading: false,
    duplicateFiles: [],
    newMasterName: null,
  };
}

const initialPage = {
  // ``new`` (upload intro), ``loading``, ``ready`` or ``denied``
  status: "new",
  projectId: null,
  videoIds: [],
  pending: 0,
  categories: [],
  categoriesLoaded: false,
  duplicateVideos: [],
};

function updateDeposit(state, id, update) {
  const deposit = state.deposits[id];
  if (!deposit) {
    return state;
  }
  return {
    ...state,
    deposits: { ...state.deposits, [id]: { ...deposit, ...update(deposit) } },
  };
}

function addVideo(state, video) {
  const id = video.metadata._deposit.id;
  if (state.deposits[id]) {
    return state;
  }
  return {
    ...state,
    page: { ...state.page, videoIds: [...state.page.videoIds, id] },
    deposits: {
      ...state.deposits,
      [id]: newDeposit("video", video.metadata, video.links, state.config),
    },
  };
}

/** The project and its videos. */
function setProject(state, project) {
  const { videos, ...metadata } = project.metadata;
  const id = metadata._deposit.id;
  let next = {
    ...state,
    page: { ...state.page, status: "ready", projectId: id, videoIds: [] },
    deposits: {
      ...state.deposits,
      [id]: newDeposit("project", metadata, project.links, state.config),
    },
  };
  (videos || []).forEach((video) => {
    next = addVideo(next, { metadata: video, links: video.links });
  });
  return next;
}

/** Merge the metadata of a response, as ``_merge`` in place did before. */
function mergeRecord(state, id, metadata) {
  const deposit = state.deposits[id];
  if (!deposit) {
    return state;
  }
  const { videos, ...own } = metadata;
  let next = updateDeposit(state, id, ({ record }) => ({
    record: _merge(_cloneDeep(record), own),
    formSync: deposit.formSync + 1,
  }));
  // The response of the project has its videos
  (deposit.type === "project" ? videos || [] : []).forEach((video) => {
    const videoId = video._deposit.id;
    if (next.deposits[videoId]) {
      next = updateDeposit(next, videoId, (entry) => ({
        record: _merge(_cloneDeep(entry.record), video),
        formSync: entry.formSync + 1,
      }));
    } else {
      next = addVideo(next, { metadata: video, links: video.links });
    }
  });
  return next;
}

function countPending(value, delta) {
  return Math.max(0, value + delta);
}

/** Server errors of a field path (and of a whole contributor). */
function withoutBackendError(errors, path) {
  const parts = _toPath(path);
  const field = parts.join(".");
  const contributor =
    parts[0] === "contributors" && parts.slice(0, -1).join(".");
  const keys = Object.keys(errors).filter(
    (key) => key === field || key === contributor
  );
  return keys.length ? _omit(errors, keys) : errors;
}

export function depositReducer(state, action) {
  switch (action.type) {
    case ActionTypes.PROJECT_SET:
      return setProject(state, action.project);
    case ActionTypes.PERMISSION_DENIED:
      return { ...state, page: { ...state.page, status: "denied" } };
    case ActionTypes.CATEGORIES_LOADED:
      return {
        ...state,
        page: {
          ...state.page,
          categories: action.categories,
          categoriesLoaded: true,
        },
      };
    case ActionTypes.VIDEO_ADDED:
      return addVideo(state, action.video);
    case ActionTypes.VIDEO_REMOVED:
      return {
        ...state,
        page: {
          ...state.page,
          videoIds: state.page.videoIds.filter((id) => id !== action.id),
        },
        deposits: _omit(state.deposits, action.id),
      };
    case ActionTypes.DUPLICATE_VIDEOS:
      return {
        ...state,
        page: { ...state.page, duplicateVideos: action.keys },
      };
    case ActionTypes.ACTION_STARTED:
    case ActionTypes.ACTION_FINISHED: {
      const delta = action.type === ActionTypes.ACTION_STARTED ? 1 : -1;
      const next = {
        ...state,
        page: {
          ...state.page,
          pending: countPending(state.page.pending, delta),
        },
      };
      return updateDeposit(next, action.id, ({ pending }) => ({
        pending: countPending(pending, delta),
      }));
    }
    case ActionTypes.DEPOSIT_PATCHED:
      return updateDeposit(state, action.id, () => action.patch);
    case ActionTypes.RECORD_REPLACED:
      // A change made by the page, not by the form: the form takes it
      return updateDeposit(state, action.id, ({ formSync }) => ({
        record: action.record,
        dirty: true,
        formSync: formSync + 1,
      }));
    case ActionTypes.RECORD_MERGED:
      return mergeRecord(state, action.id, action.metadata);
    case ActionTypes.RECORD_VALUE_SET:
      return updateDeposit(state, action.id, ({ record, backendErrors }) => ({
        record: setIn(record, action.path, _cloneDeep(action.value)),
        backendErrors: withoutBackendError(backendErrors, action.path),
        dirty: true,
      }));
    case ActionTypes.FILES_REFRESHED:
      // The files and the tasks of the server, the form changes are kept
      return updateDeposit(state, action.id, ({ record, framesReady }) => {
        const states = taskStates(action.metadata);
        return {
          record: {
            ...record,
            _files: _cloneDeep(action.metadata._files),
            _cds: { ...(record._cds || {}), state: _cloneDeep(states) },
          },
          framesReady:
            framesReady || states.file_video_extract_frames === "SUCCESS",
        };
      });
    case ActionTypes.FILES_CHANGED:
      return updateDeposit(state, action.id, ({ record }) => ({
        record: { ...record, _files: action.update(record._files || []) },
      }));
    case ActionTypes.TASK_STATE_SET:
      return updateDeposit(state, action.id, ({ record }) => ({
        record: setIn(record, ["_cds", "state", action.task], action.status),
      }));
    case ActionTypes.PRISTINE:
      return updateDeposit(state, action.id, ({ formReset }) => ({
        dirty: false,
        formReset: formReset + 1,
      }));
    case ActionTypes.FORM_ERRORS_SET:
      return updateDeposit(state, action.id, () => ({
        formErrors: action.errors,
      }));
    case ActionTypes.BACKEND_ERROR_REMOVED:
      return updateDeposit(state, action.id, ({ backendErrors }) => ({
        backendErrors: withoutBackendError(backendErrors, action.path),
      }));
    case ActionTypes.BACKEND_ERROR_ADDED:
      return updateDeposit(state, action.id, ({ backendErrors }) => ({
        backendErrors: { ...backendErrors, [action.field]: action.message },
      }));
    default:
      return state;
  }
}

export function initialState(config) {
  return {
    config,
    page: { ...initialPage, status: config.projectLinks ? "loading" : "new" },
    deposits: {},
  };
}
