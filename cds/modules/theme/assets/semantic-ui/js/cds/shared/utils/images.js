/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Thumbnails of the records, served by the IIIF image API. */

import _find from "lodash/find";
import _template from "lodash/template";

import { findContextType, findMaster, findPoster, findGif } from "./records";

const iiifTemplate = _template(
  "/api/iiif/v2/<%=bucket%>:<%=version_id%>:<%=key%>/full/!<%=size%>/0/default.<%=ext%>"
);

export const NOT_FOUND_IMAGE = "/static/img/not_found.png";

/**
 * IIIF image of a chapter frame.
 *
 * One size for every list of chapters (the strip under the player and the
 * "In this video" panel), so the browser downloads each frame once and
 * reuses it. 320 pixels covers both at the size they are displayed, up to
 * 240 pixels wide.
 */
export function chapterFrameUrl(frame) {
  return `/api/iiif/v2/${frame.bucket_id}:${frame.version_id}:${frame.key}/full/320,180/0/default.jpg`;
}

/** IIIF thumbnail of a record. */
export function iiif(record, showGif, size) {
  try {
    const masterFile = findMaster(record);
    const objectVersion = showGif ? findGif(masterFile) : findPoster(record);
    return iiifTemplate({
      bucket: objectVersion.bucket_id,
      key: objectVersion.key,
      version_id: objectVersion.version_id,
      size: size.join(","),
      ext: showGif ? "gif" : "png",
    });
  } catch (error) {
    return NOT_FOUND_IMAGE;
  }
}

/** IIIF thumbnail of a search hit. */
export function getImagePreview(record, showGif, size) {
  try {
    let file;
    if (showGif) {
      const masterFile = findContextType(record, "master");
      file = _find(
        masterFile["frames-preview"],
        (gif) => gif.key === "frames.gif"
      );
    } else {
      file = findPoster(record);
    }
    return iiifTemplate({
      bucket: file.bucket_id,
      key: file.key,
      version_id: file.version_id,
      size: size.join(","),
      ext: showGif ? "gif" : "png",
    });
  } catch (error) {
    return NOT_FOUND_IMAGE;
  }
}
