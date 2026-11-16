/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Changes of one deposit made in the page (no request). */

import _get from "lodash/get";
import _isEqual from "lodash/isEqual";

import { ActionTypes } from "./reducer";
import { forgetDeposit, isFieldRendered } from "./registry";
import { inheritMetadata as inherit, setIn } from "./records";
import { selectProjectRecord } from "./selectors";

export function patchDeposit(id, patch) {
  return { type: ActionTypes.DEPOSIT_PATCHED, id, patch };
}

/** A field of the form changed. */
export function setRecordValue(id, path, value) {
  return { type: ActionTypes.RECORD_VALUE_SET, id, path, value };
}

/** A change of the record made by the page: the form takes it. */
export function replaceRecord(id, record) {
  return { type: ActionTypes.RECORD_REPLACED, id, record };
}

/** The values of the access selects (``_access.read``, ``_access.update``). */
export function setAccess(id, path, values) {
  return (dispatch, getState) => {
    const { record } = getState().deposits[id];
    dispatch(replaceRecord(id, setIn(record, path, values)));
  };
}

/** No unsaved changes: the form is reset to the record. */
export function setPristine(id) {
  return { type: ActionTypes.PRISTINE, id };
}

export function setPristineAll() {
  return (dispatch, getState) => {
    Object.keys(getState().deposits).forEach((id) => dispatch(setPristine(id)));
  };
}

/** Errors of the client validation of the form. */
export function setFormErrors(id, errors) {
  return (dispatch, getState) => {
    const deposit = getState().deposits[id];
    if (deposit && !_isEqual(deposit.formErrors, errors)) {
      dispatch({ type: ActionTypes.FORM_ERRORS_SET, id, errors });
    }
  };
}

/** Fields not validated by the server for the form (``noValidateFields``). */
const NOT_VALIDATED = ["description"];

/** A validation error of the server, shown by its field if rendered. */
export function validationError(id, { field, message }) {
  return (dispatch) => {
    if (!NOT_VALIDATED.includes(field) && isFieldRendered(id, field)) {
      dispatch({ type: ActionTypes.BACKEND_ERROR_ADDED, id, field, message });
    }
  };
}

/** The server error of a field is gone (and of its contributor). */
export function removeBackendError(id, path) {
  return { type: ActionTypes.BACKEND_ERROR_REMOVED, id, path };
}

/** A video leaves the page (deleted). */
export function removeVideo(id) {
  return (dispatch) => {
    dispatch({ type: ActionTypes.VIDEO_REMOVED, id });
    forgetDeposit(id);
  };
}

export function changeShowAll(id, hide) {
  return patchDeposit(id, { showAll: !hide });
}

export function dismissAlert(id, index) {
  return (dispatch, getState) => {
    const { alerts } = getState().deposits[id];
    dispatch(
      patchDeposit(id, { alerts: alerts.filter((_, i) => i !== index) })
    );
  };
}

/** Copy the metadata of the project to a video (missing or all values). */
export function inheritMetadata(id, force) {
  return (dispatch, getState) => {
    const state = getState();
    const { record } = state.deposits[id];
    dispatch(
      replaceRecord(id, inherit(record, selectProjectRecord(state), force))
    );
  };
}

/* Metadata extracted from the video file */

export function dismissExtractedMetadata(id) {
  return patchDeposit(id, { metadataToFill: false });
}

/** Title of a deposit in the notifications. */
export function depositTitle(record) {
  return _get(record, "title.title") || "Video";
}
