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
 * Configuration of the deposit (the former ``cdsDeposit`` providers set in
 * ``avc.module.js``).
 */

import _template from "lodash/template";

/** Main tasks of a video, in their order (``depositStates``). */
export const DEPOSIT_STATES = [
  "file_upload",
  "file_download",
  "file_video_metadata_extraction",
  "file_video_extract_frames",
  "file_transcode",
];

/** ``depositStatuses`` */
export const DEPOSIT_STATUSES = {
  PENDING: "PENDING",
  STARTED: "STARTED",
  FAILURE: "FAILURE",
  SUCCESS: "SUCCESS",
  CANCELLED: "CANCELLED",
};

/** ``taskRepresentations`` */
export const TASK_REPRESENTATIONS = {
  file_upload: "Video file upload",
  file_download: "Video file download",
  file_transcode: "Video transcoding",
  file_video_extract_frames: "Video frame extraction",
  file_video_metadata_extraction: "Video metadata extraction",
};

/** Properties a video can inherit from its project (``inheritedProperties``). */
export const INHERITED_PROPERTIES = [
  "contributors",
  "date",
  "description",
  "keywords",
  "license",
  "title.title",
  "translations",
];

/**
 * Metadata extracted from the video file which can fill the form
 * (``depositExtractedMetadata``): each function fills ``deposit`` and
 * returns the value to display.
 */
export const DEPOSIT_EXTRACTED_METADATA = {
  title(deposit, metadata) {
    if ("title" in metadata) {
      deposit.title = { title: metadata.title };
      return metadata.title;
    }
    return undefined;
  },
  description(deposit, metadata) {
    if ("description" in metadata) {
      deposit.description = metadata.description;
      return metadata.description;
    }
    return undefined;
  },
  keywords(deposit, metadata) {
    if ("keywords" in metadata) {
      deposit.keywords = metadata.keywords.map((keyword) => ({
        name: keyword,
        value: { name: keyword },
      }));
      return metadata.keywords.join(", ");
    }
    return undefined;
  },
  date(deposit, metadata) {
    if ("creation_time" in metadata) {
      deposit.date = new Date(metadata.creation_time)
        .toISOString()
        .slice(0, 10);
      return deposit.date;
    }
    return undefined;
  },
};

const blueprints = {
  iiif: "/api/iiif/v2/<%=deposit%>:<%=version_id%>:<%=key%>/full/!<%=res%>/0/default.png",
  categories: "/api/categories",
  video: "/deposit/<%=deposit%>/preview/video/<%=key%>",
  restartTask: "/api/flows/<%=flowId%>/tasks/<%=taskId%>",
  restartFlow: "/api/flows/<%=flowId%>",
  taskFeedback: "/api/flows/<%=flowId%>/feedback",
  selfVideo: "/api/deposits/video/<%=deposit%>",
  bucketVideo: "/api/files/<%=bucket%>",
  actionVideo: "/api/deposits/video/<%=deposit%>/actions/<%=action%>",
  record: "/record/<%=recid%>",
};

/** ``urlBuilder`` */
export const urlBuilder = Object.keys(blueprints).reduce((builders, key) => {
  builders[key] = _template(blueprints[key]);
  return builders;
}, {});

/** Receiver of the video workflows (``remote-master-receiver``). */
export const FLOWS_RECEIVER = "/api/flows/";
