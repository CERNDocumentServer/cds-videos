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
 * Actions of the deposits on the server: save, publish, edit and delete
 * (the former ``cdsActions`` component).
 *
 * The requests run one after the other, in the order of the clicks, and
 * each one sends the record as it is when it starts. Two saves can not
 * overlap, so a later save can not be overwritten by an earlier one.
 */

import _cloneDeep from "lodash/cloneDeep";
import _merge from "lodash/merge";

import { toaster } from "@js/cds/components/Toaster";

import { chainedActions, cleanData, guessEndpoint, makeAction } from "../api";
import {
  depositTitle,
  dismissExtractedMetadata,
  patchDeposit,
  removeVideo,
  replaceRecord,
  setPristine,
  setPristineAll,
  validationError,
} from "./deposit";
import { ActionTypes } from "./reducer";
import { isDraft } from "./records";
import { depositStorage } from "./registry";
import { selectProject, selectProjectWithVideos } from "./selectors";

/** A queue running jobs (functions returning promises) one at a time. */
export function createQueue() {
  let last = Promise.resolve();
  return (job) => {
    const result = last.then(job, job);
    last = result.catch(() => {});
    return result;
  };
}

/** Request of an action on a deposit, with its record at this moment. */
function request(state, id, actionName) {
  const deposit = state.deposits[id];
  const record =
    deposit.type === "project"
      ? selectProjectWithVideos(state)
      : deposit.record;
  const payload = cleanData(record);
  const url = guessEndpoint(payload, deposit.type, actionName, deposit.links);
  return makeAction(url, deposit.type, actionName, payload);
}

/**
 * Save the draft videos first, then the project if it is a draft: the
 * response of the project contains the videos, which must be up to date.
 * ``except`` is a deposit that the action saves itself.
 */
function saveAllRequests(getState, except) {
  const state = getState();
  return state.page.videoIds
    .concat(state.page.projectId)
    .filter((id) => id !== except && isDraft(state.deposits[id].record))
    .map((id) => () => request(getState(), id, "SAVE_PARTIAL"));
}

function started(id) {
  return { type: ActionTypes.ACTION_STARTED, id };
}

function finished(id) {
  return { type: ActionTypes.ACTION_FINISHED, id };
}

function onSuccess(id, responses, message) {
  return (dispatch, getState) => {
    const response = Array.isArray(responses)
      ? responses[responses.length - 1]
      : responses;
    const metadata = response && response.data && response.data.metadata;
    if (metadata) {
      dispatch({ type: ActionTypes.RECORD_MERGED, id, metadata });
    }
    // ``cds.deposit.success``
    dispatch(
      patchDeposit(id, { alerts: [{ message: "Success!", type: "success" }] })
    );
    const deposit = getState().deposits[id];
    if (message !== undefined && deposit) {
      toaster.pop({
        type: "success",
        title: depositTitle(deposit.record),
        body: message,
      });
    }
    // The backend sanitizes the HTML, so wait before making it pristine
    setTimeout(() => dispatch(setPristine(id)), 50);
  };
}

function onError(id, response) {
  return (dispatch, getState) => {
    const data = response.data || {};
    if (data.status === 400 && data.errors) {
      data.errors.forEach((error) => dispatch(validationError(id, error)));
    }
    // ``cds.deposit.error``
    dispatch(
      patchDeposit(id, {
        alerts: [
          { message: data.message, type: "danger", errors: data.errors || [] },
        ],
      })
    );
    const deposit = getState().deposits[id];
    toaster.pop({
      type: "error",
      title: depositTitle(deposit ? deposit.record : {}),
      body: String(response.status || "").startsWith("5")
        ? "Internal Sever Error"
        : data.message,
    });
  };
}

/**
 * Run actions on a deposit (``SAVE_PARTIAL``, ``["SAVE", "PUBLISH"]``,
 * ...). A failure is reported, the returned promise resolves anyway.
 */
export function runActions(id, userActions) {
  return (dispatch, getState, { queue }) => {
    const names = Array.isArray(userActions) ? userActions : [userActions];
    dispatch(started(id));
    return queue(() => {
      // Publishing saves the project and its videos first, so that no change
      // of the page is lost
      const before = names.includes("PUBLISH")
        ? chainedActions(
            saveAllRequests(getState, names.includes("SAVE") ? id : null)
          )
        : Promise.resolve();
      return before.then(() => {
        // The record of the first action, as before
        const state = getState();
        const responses = chainedActions(
          names.map((name) => () => request(state, id, name))
        );
        return Array.isArray(userActions)
          ? responses
          : responses.then((all) => all[0]);
      });
    })
      .then(
        (responses) => {
          let message;
          if (names.includes("DELETE")) {
            message = "Successfully deleted.";
          } else if (names.includes("PUBLISH")) {
            message = "Successfully published.";
          }
          dispatch(onSuccess(id, responses, message));
        },
        (response) => dispatch(onError(id, response))
      )
      .finally(() => dispatch(finished(id)));
  };
}

/** Save the project and all its draft videos. */
export function saveAll() {
  return (dispatch, getState, { queue }) => {
    const project = selectProject(getState());
    if (!project) {
      return Promise.resolve();
    }
    const { id } = project;
    dispatch(started(id));
    return queue(() => chainedActions(saveAllRequests(getState)))
      .then(
        (responses) => {
          dispatch(setPristineAll());
          dispatch(onSuccess(id, responses));
        },
        (response) => dispatch(onError(id, response))
      )
      .finally(() => dispatch(finished(id)));
  };
}

/** Delete a deposit: a video leaves the page. */
export function deleteDeposit(id) {
  return (dispatch, getState) => {
    const { type } = getState().deposits[id];
    return dispatch(runActions(id, "DELETE")).then(() => {
      if (type === "video") {
        dispatch(removeVideo(id));
      }
    });
  };
}

/** Edit a published deposit, unless it is a video of a published project. */
export function editPublished(id, showCannotEditVideo) {
  return (dispatch, getState) => {
    const state = getState();
    const project = selectProject(state);
    if (
      state.deposits[id].type === "video" &&
      project.record._deposit.status === "published"
    ) {
      showCannotEditVideo();
      return;
    }
    dispatch(runActions(id, ["EDIT", "SAVE_PARTIAL"]));
    dispatch(patchDeposit(id, { showAll: true }));
  };
}

/** Publish a video, then show its brief view. */
export function publishVideo(id) {
  return (dispatch) => {
    dispatch(runActions(id, ["SAVE", "PUBLISH"]));
    dispatch(patchDeposit(id, { showAll: false }));
  };
}

/**
 * Answer to the extracted metadata suggestion: with ``answer`` the record
 * takes it and is saved. It is not suggested again in either case.
 */
export function fillMetadata(id, answer) {
  return (dispatch, getState) => {
    const { metadataToFill, record } = getState().deposits[id];
    if (answer && metadataToFill) {
      dispatch(
        replaceRecord(id, _merge(_cloneDeep(record), metadataToFill[0]))
      );
      dispatch(runActions(id, "SAVE_PARTIAL"));
    }
    depositStorage.set(id, "prompted", true);
    dispatch(dismissExtractedMetadata(id));
  };
}
