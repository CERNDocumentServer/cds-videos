/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/* Helpers of the page scripts. */

/** Call ``callback`` once the document is parsed. */
export function onReady(callback) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback);
  } else {
    callback();
  }
}

/** JSON of a data attribute or an embedded script, or ``fallback``. */
export function parseJSON(value, fallback) {
  if (!value) {
    return fallback;
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

/** Click handler of a link that runs ``fn`` instead of following it. */
export function prevent(fn) {
  return (e) => {
    e.preventDefault();
    fn();
  };
}

/**
 * Inline style hiding the element when ``condition`` is false. The element
 * stays in the page: use it only where that matters (a form, an editor or an
 * iframe keeps its state, CSS selects table rows and cells by position).
 * Elsewhere, render the element only when it is shown.
 */
export function show(condition) {
  return { display: condition ? undefined : "none" };
}

/** Dismissible alerts of the server rendered pages (``data-dismiss="alert"``). */
export function initDismissibleAlerts() {
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
