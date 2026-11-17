/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Header search form and menu toggle on small screens. */

/** Style of the plain header search form (pages without suggestions). */
export function initPlainSearchForm() {
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
export function initNavbarToggle() {
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
