/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* ``cds-record-view`` directive and ``cdsRecordCtrl`` controller. */

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import { http } from "@js/cds/api";

import { ProjectDetail } from "./project/ProjectDetail";
import { VideoDetail } from "./video/VideoDetail";

export function RecordView({
  type,
  recordUrl,
  initialRecord = undefined,
  recordViewsUrl = "",
  mediaDownloadEventUrl = "",
  relatedQueryUrl = "",
  previewLines = 10,
}) {
  // The record embedded in the page shows at once, else it is fetched
  const [record, setRecord] = useState(initialRecord || null);
  const [recordViews, setRecordViews] = useState(undefined);

  useEffect(() => {
    if (!initialRecord) {
      http.get(recordUrl).then(
        (response) => setRecord(response.data),
        () => {}
      );
    }
    if (recordViewsUrl) {
      http.get(recordViewsUrl).then(
        (response) => setRecordViews(response.data && response.data.views),
        () => {}
      );
    }
  }, [recordUrl, recordViewsUrl, initialRecord]);

  const logMediaDownload = (file) => {
    if (!mediaDownloadEventUrl || !record) {
      return;
    }
    const url = mediaDownloadEventUrl.replace("{recid}", record.metadata.recid);
    http
      .post(
        url,
        { key: file.key },
        { headers: { "Content-Type": "application/json" } }
      )
      .catch(() => {});
  };

  if (!record) {
    return null;
  }
  if (type === "project") {
    return <ProjectDetail record={record} />;
  }
  return (
    <VideoDetail
      record={record}
      recordViews={recordViews}
      previewLines={previewLines}
      relatedQueryUrl={relatedQueryUrl}
      onDownload={logMediaDownload}
    />
  );
}

RecordView.propTypes = {
  type: PropTypes.oneOf(["video", "project"]).isRequired,
  recordUrl: PropTypes.string.isRequired,
  initialRecord: PropTypes.object,
  recordViewsUrl: PropTypes.string,
  mediaDownloadEventUrl: PropTypes.string,
  relatedQueryUrl: PropTypes.string,
  previewLines: PropTypes.number,
};
