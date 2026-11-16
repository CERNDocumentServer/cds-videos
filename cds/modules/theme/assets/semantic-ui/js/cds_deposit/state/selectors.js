/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Read the deposit state. */

import _isEmpty from "lodash/isEmpty";

export const selectConfig = (state) => state.config;

export const selectPage = (state) => state.page;

/** An action of the page is running (``depositsCtrl.loading``). */
export const selectLoading = (state) => state.page.pending > 0;

export const selectDeposit = (state, id) => state.deposits[id];

export const selectProject = (state) =>
  state.page.projectId ? state.deposits[state.page.projectId] : undefined;

/** The project record, empty before the project exists. */
export const selectProjectRecord = (state) => {
  const project = selectProject(state);
  return project ? project.record : {};
};

export const selectVideos = (state) =>
  state.page.videoIds.map((id) => state.deposits[id]);

/** The project record with its videos, as the server sends it. */
export const selectProjectWithVideos = (state) => ({
  ...selectProjectRecord(state),
  videos: selectVideos(state).map((video) => video.record),
});

/** The category of the project, with its access rules. */
export const selectAccessRights = (state) => {
  const { category } = selectProjectRecord(state);
  return state.page.categories.find((item) => item.metadata.name === category);
};

export const selectAnyVideoPublished = (state) =>
  selectVideos(state).some((video) => video.record.recid);

export const selectAnyDirty = (state) =>
  Object.values(state.deposits).some((deposit) => deposit.dirty);

export function isInvalid(deposit) {
  return !_isEmpty(deposit.formErrors) || !_isEmpty(deposit.backendErrors);
}
