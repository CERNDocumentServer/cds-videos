/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Pagination of the search results. */

import React from "react";
import PropTypes from "prop-types";

import { useSearch } from "../hooks";

/** Page numbers to show in the pagination. */
export function paginationPages(total, size, page, adjacent = 4) {
  const pageCount = Math.ceil(total / size);
  const current = parseInt(page) || 1;
  const adjacentSize = 2 * adjacent;
  let start;
  let finish;
  if (pageCount <= adjacentSize + 2) {
    start = 1;
    finish = pageCount;
  } else if (current - adjacent <= 2) {
    start = 1;
    finish = 1 + adjacentSize;
  } else if (current < pageCount - (adjacent + 2)) {
    start = current - adjacent;
    finish = current + adjacent;
  } else {
    start = pageCount - adjacentSize;
    finish = pageCount;
  }
  const pages = [];
  for (let i = start; i <= finish; i++) {
    pages.push(i);
  }
  return { pages, pageCount, current };
}

/**
 * Pagination with the CDS template (``variant="cds"``,
 * Previous/Next) or the Invenio one (``variant="invenio"``, < and >).
 */
export function SearchPagination({ variant = "cds", adjacentSize = 4 }) {
  const [state, store] = useSearch();
  const total = state.results.hits ? state.results.hits.total : 0;
  if (!total) {
    return null;
  }
  const size = state.args.size;
  const { pages, pageCount, current } = paginationPages(
    total,
    size,
    state.args.page,
    adjacentSize
  );
  const changePage = (index) => {
    let page = index;
    if (index > pageCount) page = pageCount;
    else if (index < 1) page = 1;
    store.setArgs({ page });
  };
  const prevDisabled = !(current > 1);
  const nextDisabled = !(current < pageCount);
  const link = (label, page, disabled, aria) => (
    <a
      href="#page"
      aria-label={aria}
      onClick={(e) => {
        e.preventDefault();
        if (!disabled) changePage(page);
      }}
    >
      <span aria-hidden="true">{label}</span>
    </a>
  );
  return (
    <ul
      className={`cds-pagination${
        variant === "invenio" ? " cds-pagination-sm" : ""
      }`}
    >
      <li className={prevDisabled ? "disabled" : ""}>
        {link(
          variant === "invenio" ? "<" : "Previous",
          current > 1 ? current - 1 : current,
          variant !== "invenio" && prevDisabled,
          "Previous"
        )}
      </li>
      {pages.map((page) => (
        <li key={page} className={page === current ? "active" : ""}>
          <a
            href="#page"
            title={"Go to page " + page}
            onClick={(e) => {
              e.preventDefault();
              changePage(page);
            }}
          >
            {page}
          </a>
        </li>
      ))}
      <li className={nextDisabled ? "disabled" : ""}>
        {link(
          variant === "invenio" ? ">" : "Next",
          current < pageCount ? current + 1 : current,
          variant !== "invenio" && nextDisabled,
          "Next"
        )}
      </li>
    </ul>
  );
}

SearchPagination.propTypes = {
  variant: PropTypes.oneOf(["cds", "invenio"]),
  adjacentSize: PropTypes.number,
};
