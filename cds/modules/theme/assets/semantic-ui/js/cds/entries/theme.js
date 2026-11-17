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
 * ``cds_theme_app`` entry point, included in every page:
 * - header search bar with suggestions,
 * - announcement banner,
 * - search widgets of the home page and of the record page.
 */

import React from "react";
import { createRoot } from "react-dom/client";

import { onReady, initDismissibleAlerts } from "@js/cds/shared/dom";
import { SearchBarSuggestions } from "@js/cds/header/SearchBarSuggestions";
import { SearchWidget } from "@js/cds/search/components/SearchWidget";
import { toggleAnnouncement } from "@js/cds/header/announcement";
import { initPlainSearchForm, initNavbarToggle } from "@js/cds/header/navbar";

/** Mount the header search bar with suggestions (not on the search page). */
function mountSearchBar() {
  const element = document.getElementById("cds-navbar-search");
  // ``search``: mounted by the search page, ``plain``: rendered by Jinja
  if (!element || element.dataset.mode !== "suggest") return;
  createRoot(element).render(
    <SearchBarSuggestions
      action={element.dataset.action}
      placeholder={element.dataset.placeholder}
    />
  );
}

/** Mount all the search widgets of the page. */
function mountSearchWidgets() {
  document.querySelectorAll("[data-cds-search-widget]").forEach((element) => {
    const data = element.dataset;
    createRoot(element).render(
      <SearchWidget
        endpoint={data.endpoint}
        template={data.template}
        loadingMessage={data.loadingMessage || ""}
        centeredLoading={data.centeredLoading !== "false"}
      />
    );
  });
}

onReady(() => {
  toggleAnnouncement();
  initNavbarToggle();
  initDismissibleAlerts();
  mountSearchBar();
  initPlainSearchForm();
  mountSearchWidgets();
});
