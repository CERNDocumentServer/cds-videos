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
 * ``cds_search_ui_app`` entry point: the search page (``/search``).
 *
 * The page is rendered by Jinja with placeholders
 * (``[data-cds-search-component]``) which are mounted here as React roots
 * sharing one search store, as the ``invenio-search`` directives shared the
 * ``invenioSearch`` controller before.
 */

import { onReady } from "@js/cds/dom";
import { mountSearchApp } from "@js/cds/search/mount";

onReady(() => {
  const root = document.getElementById("invenio-search");
  if (root) {
    mountSearchApp(root);
  }
});
