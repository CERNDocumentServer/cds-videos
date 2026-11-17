/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Announcement banner above the header, fetched for the current page. */

import { http } from "@js/cds/shared/api";

const ANNOUNCEMENT_STYLES = {
  default: "",
  success: "positive",
  info: "info",
  warning: "warning",
  danger: "negative",
};

/** Load and show any announcement message for the current page. */
export async function toggleAnnouncement() {
  const element = document.getElementById("announcement");
  if (!element) return;
  try {
    const response = await http.get("/api/announcement", {
      params: { pathname: window.location.pathname },
      ignoreLoadingBar: true,
    });
    const result = response.data;
    if (result && result.message) {
      const style = ANNOUNCEMENT_STYLES[result.style];
      element.className = [
        "ui",
        style === undefined ? result.style : style,
        "message",
        "cds-announcement",
        "text-center",
        "alert-" + result.style,
      ]
        .filter(Boolean)
        .join(" ");
      element.innerHTML = result.message;
      // Fix the margin of the deposit view
      const deposit = document.getElementById("cds-deposit");
      if (deposit) deposit.classList.add("fix-margin-top");
    } else {
      element.classList.add("hidden");
    }
  } catch {
    // No announcement
  }
}
