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

import { http } from "./api";
import { onReady } from "./dom";
import { SearchBarSuggestions } from "./components/SearchBarSuggestions";
import { SearchWidget } from "./components/SearchWidget";

const ANNOUNCEMENT_STYLES = {
  default: "",
  success: "positive",
  info: "info",
  warning: "warning",
  danger: "negative",
};

/** Load and show any announcement message for the current page. */
export function toggleAnnouncement() {
  const element = document.getElementById("announcement");
  if (!element) return;
  http
    .get("/api/announcement", {
      params: { pathname: window.location.pathname },
      ignoreLoadingBar: true,
    })
    .then((response) => {
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
    })
    .catch(() => {});
}

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

/** Style of the plain header search form (pages without suggestions). */
function initPlainSearchForm() {
  const element = document.getElementById("cds-navbar-search");
  if (!element || element.dataset.mode !== "plain") return;
  const input = document.getElementById("cds-navbar-form-input");
  if (!input) return;
  const form = input.closest(".cds-navbar-form");
  input.addEventListener("focus", () =>
    form.classList.add("cds-active-search")
  );
  input.addEventListener("blur", () =>
    form.classList.remove("cds-active-search")
  );
}

/** Responsive navigation bar toggle. */
function initNavbarToggle() {
  document.querySelectorAll("[data-cds-navbar-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.querySelector(button.dataset.cdsNavbarToggle);
      if (target) {
        const open = target.classList.toggle("cds-navbar-collapse-open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      }
    });
  });
}

/** Dismissible alerts of the server rendered pages (``data-dismiss="alert"``). */
function initDismissibleAlerts() {
  document.addEventListener("click", (event) => {
    const button =
      event.target.closest && event.target.closest('[data-dismiss="alert"]');
    if (button) {
      const alert = button.closest(".cds-alert, .alert");
      if (alert) {
        alert.remove();
      }
    }
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
