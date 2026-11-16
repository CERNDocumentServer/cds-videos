/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* ``cds_records_stats_app`` entry point: statistics of a record. */

import * as inveniographs from "invenio-charts-js";

import { http } from "@js/cds/api";

const DEFAULT_CONFIG = {
  legend: {
    visible: false,
  },
  tooltip: {
    enabled: false,
  },
};

function toggle(id, visible) {
  const element = document.getElementById(id);
  if (element) {
    element.style.display = visible ? "" : "none";
  }
}

async function fetchRecordData(recordId, category, defaultConfig) {
  try {
    const response = await http.get(`/api/stats/${recordId}/${category}`, {
      headers: { "Content-Type": "application/json" },
    });
    toggle(`${category}-loading-spinner`, false);
    new inveniographs.LineGraph(
      response.data,
      category,
      defaultConfig
    ).render();
  } catch (error) {
    console.error(error);
    toggle(`${category}-loading-spinner`, false);
    toggle(`${category}-error-message`, true);
  }
}

function getStats(record) {
  fetchRecordData(record.recid, "media-file-download", DEFAULT_CONFIG);
}

window.getStats = getStats;
