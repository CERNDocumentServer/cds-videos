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
 * Access of the deposits: the category of the project gives
 * who can edit, and who can read when restricted. The videos follow the
 * project.
 */

import _cloneDeep from "lodash/cloneDeep";
import _get from "lodash/get";

import { saveAll } from "./actions";
import { patchDeposit, replaceRecord, setPristineAll } from "./deposit";
import {
  selectAccessRights,
  selectProject,
  selectProjectRecord,
} from "./selectors";

/** ``public`` or ``restricted``, once the project has a category. */
export function initPermissions(id) {
  return (dispatch, getState) => {
    const state = getState();
    const deposit = state.deposits[id];
    if (!deposit || !selectProjectRecord(state).category) {
      return;
    }
    let permissions;
    try {
      permissions =
        !deposit.record._access.read &&
        selectAccessRights(state).metadata.access.public
          ? "public"
          : "restricted";
    } catch (error) {
      permissions = "public";
    }
    dispatch(patchDeposit(id, { permissions }));
  };
}

/**
 * The access of a deposit from the category and its permissions. The
 * videos take the access of the project.
 */
function applyAccessRights(id) {
  return (dispatch, getState) => {
    const state = getState();
    const { record, permissions, type } = state.deposits[id];
    const accessRights = selectAccessRights(state);
    const responsible = _get(accessRights, "metadata.access.responsible");
    const access = { ...(record._access || {}) };
    delete access.read;
    access.update = [state.config.currentUserEmail].concat(
      responsible ? _cloneDeep(responsible) : []
    );
    if (permissions === "restricted") {
      access.read = _cloneDeep(
        _get(accessRights, "metadata.access.restricted")
      );
    }
    dispatch(replaceRecord(id, { ...record, _access: access }));
    if (type === "project") {
      // ``cds.deposit.video.permissions.update``
      state.page.videoIds.forEach((videoId) => {
        const video = getState().deposits[videoId];
        dispatch(patchDeposit(videoId, { permissions }));
        dispatch(
          replaceRecord(videoId, {
            ...video.record,
            _access: _cloneDeep(access),
          })
        );
      });
    }
  };
}

/** Public or restricted, chosen in the restrictions box. */
export function setPermissions(id, permissions) {
  return (dispatch) => {
    dispatch(patchDeposit(id, { permissions }));
    dispatch(applyAccessRights(id));
  };
}

/** The category or the type of the project changed: save everything. */
export function changeCategoryOrType() {
  return (dispatch, getState) => {
    const state = getState();
    const project = selectProject(state);
    const permissions = _get(
      selectAccessRights(state),
      "metadata.access.public"
    )
      ? "public"
      : "restricted";
    dispatch(setPermissions(project.id, permissions));
    dispatch(saveAll());
    dispatch(setPristineAll());
  };
}
