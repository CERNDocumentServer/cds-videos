/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* ``cds_records_app`` entry point: the record page (``/record/<recid>``). */

import React from "react";
import { createRoot } from "react-dom/client";

import { onReady, parseJSON } from "@js/cds/shared/dom";
import { mountLoadingBar } from "@js/cds/search/mount";

import { RecordView } from "@js/cds/record/RecordView";

onReady(() => {
  const element = document.getElementById("cds-record-view");
  if (!element) {
    return;
  }
  const data = element.dataset;
  // The record embedded in the page (as the API returns it)
  const embedded = document.getElementById("cds-record-json");
  createRoot(element).render(
    <RecordView
      type={data.type === "project" ? "project" : "video"}
      recordUrl={data.record}
      initialRecord={
        embedded ? parseJSON(embedded.textContent, undefined) : undefined
      }
      recordViewsUrl={data.recordViews || ""}
      mediaDownloadEventUrl={data.mediaDownloadEventUrl || ""}
      relatedQueryUrl={data.relatedQueryUrl || ""}
      previewLines={parseInt(data.previewLines, 10) || 10}
    />
  );
  mountLoadingBar();
});
