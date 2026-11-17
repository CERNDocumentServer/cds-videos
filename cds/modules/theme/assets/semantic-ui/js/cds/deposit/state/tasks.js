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
 * The video workflow of the deposits: the tasks polled while they run, the
 * files and task states refreshed from the server when they change.
 */

import _cloneDeep from "lodash/cloneDeep";
import _flatten from "lodash/flatten";
import _get from "lodash/get";
import _groupBy from "lodash/groupBy";
import _isEmpty from "lodash/isEmpty";
import _mapValues from "lodash/mapValues";

import { toaster } from "@js/cds/shared/components/Toaster";

import { action, NO_CACHE_HEADERS } from "../api";
import { DEPOSIT_STATES, urlBuilder } from "../constants";
import { patchDeposit, setPristine } from "./deposit";
import { ActionTypes } from "./reducer";
import { depositStorage } from "./registry";
import {
  anyTaskIsRunning,
  extractedMetadataToFill,
  findMasterFile,
  isPublished,
  previewerUrl,
  taskStates,
  transcodingSubformats,
} from "./records";
import { selectProject } from "./selectors";

/* Requests made in the background, without the loading bar. */
const BACKGROUND = { ignoreLoadingBar: true };

/** Extracted metadata not suggested yet (in the local storage). */
export function metadataToFill(id, metadata) {
  if (depositStorage.get(id, "prompted")) {
    return false;
  }
  return extractedMetadataToFill(
    metadata || depositStorage.get(id, "metadata")
  );
}

/** The task states of a deposit, as the reporter of the workflow. */
function initialReporter(record) {
  const reporter = {};
  DEPOSIT_STATES.forEach((task) => {
    reporter[task] = { status: "PENDING", message: task };
  });
  Object.entries(taskStates(record)).forEach(([task, status]) => {
    reporter[task] = { ...(reporter[task] || { message: task }), status };
  });
  return reporter;
}

/** Files and task states of a deposit from the server (form kept). */
function refreshDeposit(id, metadata) {
  return (dispatch, getState) => {
    const files = _cloneDeep(metadata._files);
    const subformat = _get(files, "[0].subformat");
    if (subformat) {
      // Same comparator as before (``parseInt("1080p") -> 1080``)
      subformat.sort((a, b) => parseInt(a.key, 10) < parseInt(b.key, 10));
    }
    dispatch({
      type: ActionTypes.FILES_REFRESHED,
      id,
      metadata: { ...metadata, _files: files },
    });
    const deposit = getState().deposits[id];
    if (_isEmpty(deposit.previewer)) {
      dispatch(patchDeposit(id, { previewer: previewerUrl(deposit.record) }));
    }
  };
}

/**
 * Fetch the latest data of the project and its videos, in the background:
 * the form is already shown (``cds.deposit.metadata.update.<id>``).
 */
export function refreshDeposits() {
  return async (dispatch, getState) => {
    const state = getState();
    const project = selectProject(state);
    const url =
      (project && project.links.self) || state.config.projectLinks.self;
    const response = await action(url, "GET", {}, NO_CACHE_HEADERS, BACKGROUND);
    const { metadata } = response.data;
    [metadata].concat(metadata.videos || []).forEach((depositMetadata) => {
      const id = depositMetadata._deposit.id;
      if (getState().deposits[id]) {
        dispatch(refreshDeposit(id, depositMetadata));
        // eslint-disable-next-line no-use-before-define
        dispatch(fetchTasks(id));
      }
    });
  };
}

/** A task of the workflow changed its status (``cds.deposit.task``). */
function onTaskChange(id, name, status, info) {
  return (dispatch) => {
    if (name === "file_video_metadata_extraction" && status === "SUCCESS") {
      const metadata = _get(info, "payload.extracted_metadata");
      depositStorage.set(id, "metadata", metadata);
      dispatch(
        patchDeposit(id, { metadataToFill: metadataToFill(id, metadata) })
      );
    } else if (name === "file_video_extract_frames" && status === "SUCCESS") {
      dispatch(patchDeposit(id, { framesReady: true }));
    }
  };
}

/** Report the status of a task (``updateStateReporter``). */
export function reportTask(id, name, info, status) {
  return (dispatch, getState) => {
    const deposit = getState().deposits[id];
    if (!deposit) return;
    const information = { ...(info || {}) };
    if (status && !information.status) {
      information.status = status;
    }
    const previous = deposit.stateReporter[name] || information;
    if (previous.status !== information.status) {
      dispatch(onTaskChange(id, name, information.status, information));
    }
    dispatch(
      patchDeposit(id, {
        stateReporter: {
          ...getState().deposits[id].stateReporter,
          [name]: _cloneDeep(information),
        },
      })
    );
  };
}

async function taskFeedback(flowId) {
  // Polled in the background, the tasks show their own status (in the
  // response of an error too)
  const url = urlBuilder.taskFeedback({ flowId });
  const response = await action(url, "GET", {}, undefined, BACKGROUND).catch(
    (error) => error
  );
  return _flatten(response.data, true);
}

/** Status of the tasks of the video workflow. */
export function fetchTasks(id) {
  return async (dispatch, getState) => {
    const deposit = getState().deposits[id];
    const flowId =
      deposit && _get(findMasterFile(deposit.record), "tags.flow_id");
    if (!flowId) return;
    const data = await taskFeedback(flowId);
    const current = getState().deposits[id];
    if (!current) return;
    const tasksById = _mapValues(_groupBy(data, "id"), (tasks) => tasks[0]);
    // A task changed: the files and states of the server are newer
    const cached = _isEmpty(current.tasksById) ? tasksById : current.tasksById;
    const changed = Object.keys(tasksById).some(
      (taskId) =>
        !cached[taskId] || cached[taskId].status !== tasksById[taskId].status
    );
    dispatch(
      patchDeposit(id, {
        tasksById: _cloneDeep(tasksById),
        tasksByName: _groupBy(data, "name"),
      })
    );
    if (changed) {
      dispatch(refreshDeposits());
    }
    // The subformats of the master file show the transcoding status
    const subformat = transcodingSubformats(data);
    dispatch({
      type: ActionTypes.FILES_CHANGED,
      id,
      update: (files) =>
        files.map((file) =>
          file.context_type === "master" ? { ...file, subformat } : file
        ),
    });
    (data || []).forEach((task) =>
      dispatch(reportTask(id, task.name, task.info, task.status))
    );
  };
}

export function restartFlow(id) {
  return async (dispatch, getState) => {
    const flowId = _get(
      findMasterFile(getState().deposits[id].record),
      "tags.flow_id"
    );
    try {
      await action(urlBuilder.restartFlow({ flowId }), "PUT");
    } catch {
      toaster.pop({ type: "error", title: "Flow cannot be restarted!" });
      return;
    }
    toaster.pop({ type: "info", title: "Flow has been restarted!" });
    dispatch(fetchTasks(id));
  };
}

export function restartTask(id, flowId, taskId) {
  return async (dispatch) => {
    await action(urlBuilder.restartTask({ taskId, flowId }), "PUT");
    return dispatch(fetchTasks(id));
  };
}

/**
 * A deposit is shown (``$onInit`` and ``$postLink``): poll its tasks while
 * they run. Returns the function stopping it.
 */
export function startDeposit(id) {
  return (dispatch, getState) => {
    const { record, type } = getState().deposits[id];
    if (isPublished(record)) {
      depositStorage.remove(id);
    }
    dispatch(
      patchDeposit(id, {
        metadataToFill: type === "video" ? metadataToFill(id) : false,
        stateReporter: initialReporter(record),
        previewer: previewerUrl(record),
      })
    );
    dispatch(fetchTasks(id));
    const interval = setInterval(() => {
      const deposit = getState().deposits[id];
      if (deposit && anyTaskIsRunning(deposit.record)) {
        dispatch(fetchTasks(id));
      }
    }, 5000);
    const pristine = setTimeout(() => dispatch(setPristine(id)), 1500);
    return () => {
      clearInterval(interval);
      clearTimeout(pristine);
    };
  };
}
