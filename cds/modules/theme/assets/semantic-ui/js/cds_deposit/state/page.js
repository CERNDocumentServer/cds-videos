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
 * The deposit page (the former ``cdsDeposits`` component): the project and
 * its videos, created from the video files of a new upload.
 */

import _isEmpty from "lodash/isEmpty";
import _omit from "lodash/omit";

import { http } from "@js/cds/api";
import { toaster } from "@js/cds/components/Toaster";

import { getUrlPath, makeAction, resolveJSON } from "../api";
import { urlBuilder } from "../constants";
import { ActionTypes } from "./reducer";
import { depositStorage } from "./registry";
import { initPermissions } from "./permissions";
import { filterOutFiles, findMasterFile, withKeywords } from "./records";
import { selectAnyDirty, selectProject, selectVideos } from "./selectors";
import { refreshDeposits } from "./tasks";
import { localFile, queueUpload } from "./uploads";

/** The project and its videos (``files`` of a new project). */
export function setProject(project, files) {
  const metadata = withKeywords(project.metadata);
  if (_isEmpty(metadata._files)) {
    metadata._files = files || [];
  }
  return { type: ActionTypes.PROJECT_SET, project: { ...project, metadata } };
}

function handleRedirect(url) {
  if (url) {
    window.history.replaceState(window.history.state, "", getUrlPath(url));
  }
}

/** Refresh the project and its tasks once it is set, at its own URL. */
function afterProject() {
  return (dispatch, getState) => {
    dispatch(refreshDeposits());
    handleRedirect(selectProject(getState()).links.html);
  };
}

/** Warn the user once if there are any unsaved changes. */
function warnBeforeUnload(getState) {
  let warned = false;
  return (event) => {
    if (!warned && selectAnyDirty(getState())) {
      warned = true;
      event.preventDefault();
      // eslint-disable-next-line no-param-reassign
      event.returnValue = "Unsaved changes have been detected.";
      return "Unsaved changes have been detected.";
    }
    return undefined;
  };
}

/**
 * Load the categories and the project (unless it is embedded in the page).
 * Returns the function stopping the page.
 */
export function initPage() {
  return (dispatch, getState) => {
    http
      .get(urlBuilder.categories())
      .then((response) => {
        dispatch({
          type: ActionTypes.CATEGORIES_LOADED,
          categories: response.data.hits.hits,
        });
        Object.keys(getState().deposits).forEach((id) =>
          dispatch(initPermissions(id))
        );
      })
      .catch(() => {});
    const { config, page } = getState();
    if (config.projectLinks) {
      if (page.status === "ready") {
        // Embedded in the page: refresh it as if it had just been fetched
        dispatch(afterProject());
      } else {
        resolveJSON(config.projectLinks.self).then(
          (response) => {
            dispatch(setProject(response.data));
            dispatch(afterProject());
          },
          (response) => {
            if (response.status === 403) {
              dispatch({ type: ActionTypes.PERMISSION_DENIED });
            }
          }
        );
      }
    }
    const onBeforeUnload = warnBeforeUnload(getState);
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  };
}

function createDeposit(url, schema, type, extra) {
  return makeAction(url, type, "CREATE", { $schema: schema, ...(extra || {}) });
}

/** Create the project of a new upload, with its other files. */
function createProject(files) {
  return (dispatch, getState) => {
    const { projectInit, projectSchema } = getState().config;
    const unique = files.filter(
      (file, index) =>
        files.findIndex((other) => other.key === file.key) === index
    );
    return createDeposit(projectInit, projectSchema, "project")
      .then((response) => {
        dispatch(setProject(response.data, unique));
        dispatch(afterProject());
        return resolveJSON(response.data.links.self);
      })
      .then((response) => {
        const { id } = selectProject(getState());
        dispatch({
          type: ActionTypes.RECORD_MERGED,
          id,
          metadata: response.data.metadata,
        });
        dispatch({
          type: ActionTypes.DEPOSIT_PATCHED,
          id,
          patch: {
            links: {
              ...selectProject(getState()).links,
              ...response.data.links,
            },
          },
        });
      });
  };
}

/** A new video of the project, with its files to upload. */
function addVideo(response, files, entries) {
  return (dispatch, getState) => {
    const id = response.data.metadata._deposit.id;
    dispatch({
      type: ActionTypes.VIDEO_ADDED,
      video: {
        metadata: { ...response.data.metadata, _files: entries },
        links: response.data.links,
      },
    });
    files.forEach((file, index) => queueUpload(id, file, entries[index]));
    if (getState().page.categoriesLoaded) {
      dispatch(initPermissions(id));
    }
  };
}

/** Video files of a new upload: create the project if needed, one video each. */
export function addVideoFiles(newFiles, invalidFiles) {
  return (dispatch, getState) => {
    if (!newFiles) {
      return Promise.resolve();
    }
    const { config, page } = getState();
    const files = newFiles.filter(
      (file) => !(invalidFiles || []).includes(file)
    );
    const local = files.map((file) => ({ ...localFile(file), file }));
    const filtered = filterOutFiles(local, config.videoExtensions);
    const strip = (entry) => _omit(entry, "file");
    let project;
    if (page.status === "ready") {
      const { id } = selectProject(getState());
      dispatch({
        type: ActionTypes.FILES_CHANGED,
        id,
        update: (current) => current.concat(filtered.project.map(strip)),
      });
      project = Promise.resolve();
    } else {
      project = dispatch(createProject(filtered.project.map(strip)));
    }
    return project.then(() => {
      const state = getState();
      const projectId = selectProject(state).id;
      const uploaded = selectVideos(state)
        .map((video) => findMasterFile(video.record))
        .filter((master) => !_isEmpty(master))
        .map((master) => master.key);
      const duplicates = Object.values(filtered.videos)
        .map((video) => video.key)
        .filter((key) => uploaded.includes(key));
      dispatch({ type: ActionTypes.DUPLICATE_VIDEOS, keys: duplicates });
      if (duplicates.length > 0) {
        toaster.pop({
          type: "error",
          title: "Duplicate video(s)!",
          body: duplicates.join(", "),
        });
      }
      if ((invalidFiles || []).length > 0) {
        toaster.pop({
          type: "error",
          title: "Invalid file(s)",
          body: invalidFiles.map((file) => file.name).join(", "),
        });
      }
      // One video after the other, in the order of the files
      return Object.entries(filtered.videos)
        .filter(([, video]) => !duplicates.includes(video.key))
        .reduce(
          (previous, [basename, video]) =>
            previous.then(() =>
              createDeposit(config.videoInit, config.videoSchema, "video", {
                _project_id: projectId,
                title: { title: basename },
              }).then((response) => {
                // From the deposit to the video basename (local storage)
                depositStorage.set(
                  response.data.metadata._deposit.id,
                  "basename",
                  basename
                );
                const related = filtered.videoFiles[basename] || [];
                const all = [video].concat(related);
                dispatch(
                  addVideo(
                    response,
                    all.map((item) => item.file),
                    all.map(strip)
                  )
                );
              })
            ),
          Promise.resolve()
        )
        .catch(() => {});
    });
  };
}
