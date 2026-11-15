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
 * ``cds_deposit_app`` entry point: the deposit page (``#cds-deposit``) and
 * the list of the deposits (``#cds-deposit-index``).
 */

import React from "react";
import { createRoot } from "react-dom/client";

import { onReady, parseJSON } from "@js/cds/dom";
import { mountSearchApp } from "@js/cds/search/mount";

import { Deposits } from "./components/Deposits";
import {
  DEPOSIT_INDEX_COMPONENTS,
  DEPOSIT_INDEX_PLACEHOLDERS,
  DEPOSIT_INDEX_TEMPLATES,
} from "./index/components";
import { createDepositStore } from "./state/store";

function maxNumberOfVideos() {
  const element = document.getElementById("max-n-videos-per-project");
  return element && element.value ? parseInt(element.value, 10) : 10;
}

/** The project embedded in the edit page (``#cds-deposit-project``). */
function embeddedProject() {
  const element = document.getElementById("cds-deposit-project");
  return element ? parseJSON(element.textContent, undefined) : undefined;
}

function mountDeposits(element) {
  const data = element.dataset;
  const config = {
    projectInit: data.projectInit,
    projectLinks: data.projectLinks
      ? parseJSON(data.projectLinks, undefined)
      : undefined,
    projectSchema: data.projectSchema,
    videoInit: data.videoInit,
    videoSchema: data.videoSchema,
    videoExtensions: data.videoExtensions,
    showAvcRestrictedFields: data.showAvcRestrictedFields === "true",
    isSuperAdmin: data.isSuperAdmin === "true",
    currentUserEmail: data.currentUserEmail,
    maxNumberOfVideos: maxNumberOfVideos(),
  };
  const store = createDepositStore(
    config,
    data.projectLinks ? embeddedProject() : undefined
  );
  // No loading bar: the form shows placeholders while loading, and its own
  // spinner during the actions
  createRoot(element).render(<Deposits store={store} />);
}

onReady(() => {
  const deposits = document.getElementById("cds-deposit");
  if (deposits) {
    mountDeposits(deposits);
  }

  const index = document.getElementById("cds-deposit-index");
  if (index) {
    mountSearchApp(index, {
      components: DEPOSIT_INDEX_COMPONENTS,
      templates: DEPOSIT_INDEX_TEMPLATES,
      placeholders: DEPOSIT_INDEX_PLACEHOLDERS,
    });
  }
});
