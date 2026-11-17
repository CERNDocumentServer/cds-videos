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
 * File uploads of the deposits.
 *
 * A local file is shown in ``_files`` as ``{key, size, type, local, ...}``
 * with its upload progress. The ``File`` itself waits in the upload queue
 * of the deposit, outside of the state.
 */

import _merge from "lodash/merge";

import { getCookie, http } from "@js/cds/shared/api";
import { toaster } from "@js/cds/shared/components/Toaster";
import { ISO_LANGUAGES } from "@js/cds/shared/utils/languages";

import { FLOWS_RECEIVER, urlBuilder } from "../constants";
import { patchDeposit } from "./deposit";
import { ActionTypes } from "./reducer";
import { uploadQueue } from "./registry";
import { filterOutFiles, findMasterFile, videoBasename } from "./records";
import { refreshDeposits, reportTask } from "./tasks";

/** A local file in the list of files of a deposit. */
export function localFile(file, extra) {
  return {
    key: file.name,
    name: file.name,
    size: file.size,
    type: file.type,
    local: true,
    ...(extra || {}),
  };
}

/** Queue the upload of a ``File`` shown as ``entry``. */
export function queueUpload(id, file, entry, headers) {
  uploadQueue(id).push({ file, key: entry.key, entry, headers });
}

function changeFiles(id, update) {
  return { type: ActionTypes.FILES_CHANGED, id, update };
}

function updateFile(id, key, data, replace) {
  return changeFiles(id, (files) =>
    files.map((file) =>
      file.key === key ? (replace ? data : { ...file, ...data }) : file
    )
  );
}

function preventBrowserClose(event) {
  event.preventDefault();
  // eslint-disable-next-line no-param-reassign
  event.returnValue = "";
}

function toResponse(error) {
  return (error && error.response) || { data: {}, status: 0 };
}

/** Progress of the upload of a new video (no master file yet). */
function reportUpload(id, status, percentage) {
  return (dispatch, getState) => {
    if (!findMasterFile(getState().deposits[id].record)) {
      dispatch(
        reportTask(
          id,
          "file_upload",
          { payload: { percentage: percentage || 0 } },
          status
        )
      );
    }
  };
}

function setUploadState(id, status) {
  return { type: ActionTypes.TASK_STATE_SET, id, task: "file_upload", status };
}

/** Upload a local file, then start the video workflow of a video file. */
function uploadFile(id, { file, key, headers, entry }) {
  return async (dispatch, getState) => {
    const { record } = getState().deposits[id];
    const extensions = getState().config.videoExtensions;
    const bucket = record._buckets.deposit;
    dispatch(setUploadState(id, "STARTED"));
    let response;
    try {
      response = await http.request({
        url: `${urlBuilder.bucketVideo({ bucket })}/${key}`,
        method: "PUT",
        headers: {
          "Content-Type": (file.type || "").indexOf("/") > -1 ? file.type : "",
          "X-CSRFToken": getCookie("csrftoken"),
          ...(headers || {}),
        },
        data: file,
        // The video panel shows the progress of the upload
        ignoreLoadingBar: true,
        // The file is the raw body of the request
        transformRequest: [(data) => data],
        onUploadProgress: (event) => {
          const total = event.total || file.size || 1;
          const percentage = parseInt((100.0 * event.loaded) / total, 10);
          dispatch(reportUpload(id, "STARTED", percentage));
          dispatch(
            updateFile(id, key, { percentage, completed: percentage === 100 })
          );
        },
      });
    } catch (error) {
      dispatch(reportUpload(id, "FAILURE"));
      throw toResponse(error);
    }
    dispatch(setUploadState(id, "SUCCESS"));
    const data = { ...response.data, percentage: 100, completed: true };
    dispatch(
      updateFile(id, key, data.tags ? _merge({}, data, data.tags) : data, true)
    );
    dispatch(reportUpload(id, "SUCCESS", 100));
    if (!entry.isAdditional && videoBasename(key, extensions) !== null) {
      const workflow = await http.request({
        method: "POST",
        url: FLOWS_RECEIVER,
        headers: { "Content-Type": "application/json" },
        data: {
          version_id: response.data.version_id,
          key,
          bucket_id: bucket,
          deposit_id: id,
        },
        ignoreLoadingBar: true,
      });
      dispatch(patchDeposit(id, { presets: workflow.data.presets }));
    }
    dispatch(refreshDeposits());
    return response;
  };
}

/** Upload the queue of a deposit, one file after the other. */
export function upload(id) {
  return async (dispatch) => {
    const queue = uploadQueue(id);
    if (queue.length === 0) {
      dispatch(patchDeposit(id, { waitingUpload: false }));
      return;
    }
    window.addEventListener("beforeunload", preventBrowserClose);
    dispatch(patchDeposit(id, { uploading: true }));
    const keys = [];
    try {
      while (queue.length > 0) {
        const response = await dispatch(uploadFile(id, queue.shift()));
        keys.push(response.data.key);
      }
      toaster.pop({
        type: "info",
        title: "The file(s) has been successfully uploaded.",
        body: keys.join(", "),
      });
    } catch (response) {
      toaster.pop({
        type: "error",
        title:
          response.status === 400 && response.data && response.data.message
            ? response.data.message
            : "Error uploading the file(s).",
      });
    } finally {
      dispatch(patchDeposit(id, { waitingUpload: false, uploading: false }));
      window.removeEventListener("beforeunload", preventBrowserClose);
    }
  };
}

/**
 * A new video waits a moment for its view, then uploads its file. Returns
 * the function cancelling it.
 */
export function startUploads(id) {
  return (dispatch, getState) => {
    const deposit = getState().deposits[id];
    if (deposit.type !== "video" || uploadQueue(id).length === 0) {
      return () => {};
    }
    dispatch(patchDeposit(id, { waitingUpload: true }));
    const timeout = setTimeout(() => dispatch(upload(id)), 1500);
    return () => clearTimeout(timeout);
  };
}

function invalidFilesToast(record, invalidFiles) {
  if ((invalidFiles || []).length > 0) {
    toaster.pop({
      type: "error",
      title: `Invalid file(s) for ${record.title.title || "video."}`,
      body: invalidFiles.map((file) => file.name).join(", "),
    });
  }
}

/** Additional files (subtitles, posters, other files), uploaded at once. */
export function addFiles(id, newFiles, invalidFiles) {
  return (dispatch, getState) => {
    if (!newFiles) {
      return;
    }
    const files = newFiles
      .filter((file) => !(invalidFiles || []).includes(file))
      .filter((file) => {
        const name = file.name.toLowerCase();
        const subtitle = name.endsWith(".vtt") || name.endsWith(".srt");
        if ((!file.type || file.type.trim() === "") && !subtitle) {
          toaster.pop(
            "warning",
            "Invalid File Type",
            `The file ${file.name} has no valid type.`
          );
          return false;
        }
        if (!file.size) {
          toaster.pop(
            "warning",
            "Empty File",
            `The file ${file.name} is empty and cannot be uploaded.`
          );
          return false;
        }
        return true;
      });
    const entries = files.map((file) =>
      localFile(file, { isAdditional: true })
    );
    // Replaced files (same filename) are removed from the list
    const keys = entries.map((entry) => entry.key);
    dispatch(
      changeFiles(id, (current) =>
        current.filter((file) => !keys.includes(file.key)).concat(entries)
      )
    );
    invalidFilesToast(getState().deposits[id].record, invalidFiles);
    files.forEach((file, index) =>
      queueUpload(id, file, entries[index], {
        "X-Invenio-File-Tags": "context_type=additional_file",
      })
    );
    dispatch(upload(id));
  };
}

/* A new video file replacing the master file of a video */

const replacements = new Map();

export function replaceMasterFile(id, newFiles, invalidFiles) {
  return (dispatch, getState) => {
    if (!newFiles) {
      return;
    }
    const { record, type } = getState().deposits[id];
    const { videoExtensions } = getState().config;
    const files = newFiles.filter(
      (file) => !(invalidFiles || []).includes(file)
    );
    const masterFile = findMasterFile(record) || {};
    const videos = Object.values(
      filterOutFiles(
        files.map((file) => ({ key: file.name, file })),
        videoExtensions
      ).videos
    );
    invalidFilesToast(record, invalidFiles);
    if (type !== "video" || videos.length === 0) {
      return;
    }
    const { file } = videos[0];
    const timesReplaced =
      masterFile.tags && masterFile.tags.times_replaced
        ? parseInt(masterFile.tags.times_replaced, 10) + 1
        : 1;
    replacements.set(id, () => {
      const entry = localFile(file, { key: masterFile.key });
      dispatch(
        changeFiles(id, (current) =>
          current.filter((item) => item.key !== masterFile.key).concat(entry)
        )
      );
      queueUpload(id, file, entry, {
        "X-Invenio-File-Tags": `times_replaced=${timesReplaced}`,
      });
      dispatch(patchDeposit(id, { previewer: null }));
      dispatch(upload(id));
    });
    // Asked first
    dispatch(patchDeposit(id, { newMasterName: file.name }));
  };
}

export function closeNewMasterDialog(id, confirm) {
  return (dispatch) => {
    const replace = replacements.get(id);
    replacements.delete(id);
    dispatch(patchDeposit(id, { newMasterName: null }));
    if (confirm && replace) {
      replace();
    }
  };
}

/** Remove a file, from the server once uploaded. */
export function removeFile(id, key) {
  return async (dispatch, getState) => {
    const file = (getState().deposits[id].record._files || []).find(
      (item) => item.key === key
    );
    if (!file) return;
    const remove = changeFiles(id, (files) =>
      files.filter((item) => item.key !== key)
    );
    if (file.links === undefined) {
      const queue = uploadQueue(id);
      const index = queue.findIndex((item) => item.key === key);
      if (index > -1) {
        queue.splice(index, 1);
      }
      dispatch(remove);
      return;
    }
    try {
      await http.request({
        url: file.links.version || file.links.deleteFile,
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
    } catch {
      toaster.pop({ type: "error", title: "Error deleting the file." });
      return;
    }
    dispatch(remove);
    toaster.pop({
      type: "success",
      title: "The file has been succesfuly deleted.",
    });
  };
}

/* Helpers of the file lists */

export function thumbnailPreview(frame) {
  return urlBuilder.iiif({
    deposit: frame.bucket_id,
    key: frame.key,
    res: "150,100",
    version_id: frame.version_id,
  });
}

/** Subtitles named with a language code, i.e. ``jessica_jones-en.vtt``. */
export function validateSubtitles(file) {
  const match = file.name.match(/(?:.+)[_|-]([a-zA-Z]{2})\.(vtt|srt)/) || [];
  return match.length > 1 && match[1] in ISO_LANGUAGES;
}

export function validateAdditionalFiles(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith(".vtt") || name.endsWith(".srt")) {
    return validateSubtitles(file);
  }
  return true;
}
