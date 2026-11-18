/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Read the files and the access of a record. */

import _find from "lodash/find";
import _get from "lodash/get";
import _groupBy from "lodash/groupBy";
import _isArray from "lodash/isArray";
import _isEmpty from "lodash/isEmpty";
import _orderBy from "lodash/orderBy";

import { filterByFields } from "./collections";

/** Find record's file with given context_type. */
export function findContextType(record, contextType) {
  if (!_isEmpty(record)) {
    const files = record.metadata ? record.metadata._files : record._files;
    return _find(files, (file) => file.context_type === contextType);
  }
  return undefined;
}

/** Find master video file in record's files. */
export function findMaster(record) {
  return findContextType(record, "master");
}

/** Find master video's frames, without the chapter frames. */
export function findFrames(record) {
  if (!record) return [];
  const master = findMaster(record);
  if (!master || !master.frame) return [];
  return master.frame.filter((frame) => !_get(frame, "tags.is_chapter_frame"));
}

/** Find closest video resolution label for a file. */
export function findResolution(file) {
  const height = parseInt(file.tags.height, 10);
  const width = parseInt(file.tags.width, 10);

  let selectedResolution = height.toString().concat("p");

  const heightsToQualities = {
    240: "240p",
    360: "360p",
    480: "480p",
    720: "720p",
    1024: "1024p",
    1080: "TBD",
    2160: "4K",
    4320: "8K",
  };

  Object.keys(heightsToQualities).forEach((resolution) => {
    if (height >= resolution) {
      selectedResolution = heightsToQualities[resolution];
    }
  });

  if (selectedResolution === "TBD") {
    const widthToQualities = {
      1920: "1080p",
      2048: "2K",
    };
    selectedResolution = widthToQualities[1920];
    Object.keys(widthToQualities).forEach((resolution) => {
      if (width >= resolution) {
        selectedResolution = widthToQualities[resolution];
      }
    });
  }
  return selectedResolution;
}

/** Find the poster of a record, or the first frame of the master file. */
export function findPoster(record) {
  const poster = findContextType(record, "poster");
  if (poster) {
    return poster;
  }
  const masterFile = findMaster(record);
  return _find(masterFile["frame"], (frame) => frame.key === "frame-1.jpg");
}

/** Find the gif animation of a master video file. */
export function findGif(masterFile) {
  return _find(masterFile["frames-preview"], (gif) => gif.key === "frames.gif");
}

/** Split files in ``download`` and ``additional`` groups. */
export function groupDownloadable(items) {
  return _groupBy(items, (e) =>
    _get(e, "tags.download") === "true" ? "download" : "additional"
  );
}

/** Sort video subformats descending by height. */
export function sortVideosDescending(videos) {
  return _orderBy(videos, (video) => parseInt(video.tags.height), ["desc"]);
}

/** Files with the given media types. */
export function getFilesByType(files, types) {
  if (!_isArray(files) || !_isArray(types) || !types.length || !files.length) {
    return files;
  }
  return files.filter((file) => types.indexOf(file.media_type) !== -1);
}

/** Files without the given media types. */
export function getAllFilesExcept(files, types) {
  if (!_isArray(files) || !_isArray(types) || !types.length || !files.length) {
    return files;
  }
  return files.filter((file) => types.indexOf(file.media_type) === -1);
}

/** ``_access.status`` of the REST API: everyone gets it, only the editors
 * get who can read the record (``_access.read``). */
export function isPublic(record) {
  return _get(record, "_access.status") !== "restricted";
}

/** Subtitle files of a record usable as transcripts (``vtt`` subtitles). */
export function getVttSubtitles(record) {
  return filterByFields(_get(record, "metadata._files"), {
    context_type: "subtitle",
    content_type: "vtt",
  });
}
