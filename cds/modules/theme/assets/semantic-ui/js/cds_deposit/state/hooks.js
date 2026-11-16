/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* The deposit state in the components. */

import { useEffect, useMemo } from "react";
import { useDispatch, useSelector } from "react-redux";

import {
  deleteDeposit,
  editPublished,
  fillMetadata,
  publishVideo,
  runActions,
  saveAll,
} from "./actions";
import {
  changeShowAll,
  dismissAlert,
  dismissExtractedMetadata,
  inheritMetadata,
  setAccess,
  setRecordValue,
} from "./deposit";
import { changeCategoryOrType, setPermissions } from "./permissions";
import { depositStatus } from "./records";
import {
  selectAccessRights,
  selectAnyVideoPublished,
  selectConfig,
  selectLoading,
  selectPage,
  selectProjectRecord,
} from "./selectors";
import { restartFlow, restartTask } from "./tasks";
import {
  addFiles,
  closeNewMasterDialog,
  removeFile,
  replaceMasterFile,
} from "./uploads";

/** Settings of the page (they never change). */
export function useConfig() {
  return useSelector(selectConfig);
}

export function usePage() {
  return useSelector(selectPage);
}

/** An action of the page is running. */
export function useLoading() {
  return useSelector(selectLoading);
}

export function useDeposit(id) {
  return useSelector((state) => state.deposits[id]);
}

export function useProjectRecord() {
  return useSelector(selectProjectRecord);
}

export function useAccessRights() {
  return useSelector(selectAccessRights);
}

export function useAnyVideoPublished() {
  return useSelector(selectAnyVideoPublished);
}

/** Status of the tasks of a deposit: ``{status, startedTask}``. */
export function useDepositStatus(id) {
  const states = useSelector(
    (state) => state.deposits[id] && state.deposits[id].record._cds
  );
  return useMemo(() => depositStatus({ _cds: states }), [states]);
}

/** Run a thunk returning a stop function while the component is shown. */
export function useStarted(start, id) {
  const dispatch = useDispatch();
  useEffect(() => dispatch(start(id)), [dispatch, start, id]);
}

/** The actions of a deposit. */
export function useDepositActions(id) {
  const dispatch = useDispatch();
  return useMemo(
    () => ({
      setValue: (path, value) => dispatch(setRecordValue(id, path, value)),
      run: (actions) => dispatch(runActions(id, actions)),
      saveAll: () => dispatch(saveAll()),
      publishVideo: () => dispatch(publishVideo(id)),
      remove: () => dispatch(deleteDeposit(id)),
      editPublished: (showCannotEdit) =>
        dispatch(editPublished(id, showCannotEdit)),
      changeShowAll: (hide) => dispatch(changeShowAll(id, hide)),
      dismissAlert: (index) => dispatch(dismissAlert(id, index)),
      inheritMetadata: (force) => dispatch(inheritMetadata(id, force)),
      fillMetadata: (answer) => dispatch(fillMetadata(id, answer)),
      dismissExtractedMetadata: () => dispatch(dismissExtractedMetadata(id)),
      setAccess: (path, values) => dispatch(setAccess(id, path, values)),
      setPermissions: (permissions) =>
        dispatch(setPermissions(id, permissions)),
      changeCategoryOrType: () => dispatch(changeCategoryOrType()),
      restartFlow: () => dispatch(restartFlow(id)),
      restartTask: (flowId, taskId) =>
        dispatch(restartTask(id, flowId, taskId)),
      addFiles: (files, invalid) => dispatch(addFiles(id, files, invalid)),
      replaceMasterFile: (files, invalid) =>
        dispatch(replaceMasterFile(id, files, invalid)),
      closeNewMasterDialog: (confirm) =>
        dispatch(closeNewMasterDialog(id, confirm)),
      removeFile: (key) => dispatch(removeFile(id, key)),
    }),
    [dispatch, id]
  );
}
