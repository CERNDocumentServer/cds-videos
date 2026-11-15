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
 * React versions of the invenio-search-js directives, rendering the same
 * markup as the CDS templates of the previous interface.
 */

import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { Dropdown, Message, Segment } from "semantic-ui-react";

import {
  angularFilter,
  collectionLabel,
  isoToLanguage,
  joinArray,
} from "../utils";
import { FacetsPlaceholder, LinePlaceholder } from "../components/Placeholders";
import { useSearch } from "./hooks";

// The year histogram draws with d3 (about 150 KB): load it with the first
// year facet only, instead of on every page that shows search results
let histogram;
function loadHistogram() {
  histogram = histogram || import("./rangeHistogram");
  return histogram;
}

/** True until the first results (or error) of the search arrive. */
export function isFirstLoad(state) {
  return !state.results.hits && !state.error;
}

/** ``invenio-search-loading`` */
export function SearchLoading({ message = "", className = null }) {
  const [state] = useSearch();
  if (!state.loading) {
    return null;
  }
  return (
    <div className={["loading", className].filter(Boolean).join(" ")}>
      <i className="fa fa-spinner" /> {message}
    </div>
  );
}

SearchLoading.propTypes = {
  message: PropTypes.string,
  className: PropTypes.string,
};

/** ``invenio-search-error`` (cds_search_ui/error.html) */
export function SearchError() {
  const [state] = useSearch();
  if (!(state.error && state.errorResults && state.errorResults.message)) {
    return null;
  }
  return (
    <Message negative className="cds-search-error">
      <i className="fa fa-bolt" />
      <strong>Error:</strong> {state.errorResults.message}
    </Message>
  );
}

/** ``invenio-search-count`` (cds_search_ui/count.html) */
export function SearchCount() {
  const [state] = useSearch();
  const total = state.results.hits ? state.results.hits.total : undefined;
  // The count of the previous search would describe the placeholders
  if (state.loading || isFirstLoad(state)) {
    return <LinePlaceholder className="cds-placeholder-count" />;
  }
  if (total === 0) {
    const params = state.currentParams || {};
    return (
      <div>
        <Segment secondary className="cds-well">
          <div className="text-center mb-20">
            <i className="fa fa-search f2" />
          </div>
          <p className="f5">no results found</p>
          {Object.keys(params)
            .filter((key) => ["page", "size"].indexOf(key) === -1)
            .map((key) => {
              const value = params[key];
              return (
                <div key={key}>
                  {key === "q" && value !== "" && (
                    <p className="f6">
                      for &quot;<em>{value}</em>&quot;
                    </p>
                  )}
                  {key !== "q" && (
                    <p>
                      <strong className="text-capitalize">{key + ":"}</strong>{" "}
                      <em>{isoToLanguage(joinArray(value))}</em>
                    </p>
                  )}
                </div>
              );
            })}
          <p />
        </Segment>
      </div>
    );
  }
  if (total > 0) {
    return (
      <div>{total === 1 ? "Found 1 result" : `Found ${total} results`}</div>
    );
  }
  return null;
}

function facetValues(currentParams, key) {
  const value = currentParams[key];
  if (value === undefined) return [];
  return typeof value === "string" ? [value] : value;
}

/** Toggle a facet value (``handleClick`` of ``invenio-search-facets``). */
function toggleFacet(state, store, key, value) {
  let values = state.currentParams[key];
  values = values === undefined ? [] : values;
  if (typeof values === "string") {
    values = [values];
  } else {
    values = [...values];
  }
  const index = values.indexOf(value);
  if (index === -1) {
    values.push(value);
  } else {
    values.splice(index, 1);
  }
  store.changeParams({ [key]: values });
}

/** ``invenio-search-facets`` (cds_search_ui/facets.html) */
export function SearchFacets() {
  const [state, store] = useSearch();
  const results = state.results;
  if (isFirstLoad(state)) {
    return (
      <div className="cds-search-facets bg-w pt-30">
        <FacetsPlaceholder count={3} />
      </div>
    );
  }
  if (!(results.hits && results.hits.total > 0)) {
    return null;
  }
  const aggregations = results.aggregations || {};
  return (
    <div className="cds-search-facets bg-w pt-30">
      {Object.keys(aggregations).map((key) => {
        const value = aggregations[key];
        const values = facetValues(state.currentParams, key);
        if (
          !((value.buckets || []).length > 0 || values.length) ||
          key === "years"
        ) {
          return null;
        }
        return (
          <div key={key} className="cds-border ba mb-30 pa-10 b-r-3">
            <h2 className="text-capitalize f8 mt-5">
              <b>{key}</b>
            </h2>
            {(value.buckets || []).map((item) => {
              const checked = values.indexOf(item.key) > -1;
              // With a collection filter active, hide the other collection options
              const hidden =
                key === "collections" &&
                values.length &&
                values.indexOf(item.key) === -1;
              let label = item.key;
              if (key === "language") label = isoToLanguage(item.key);
              if (key === "collections") label = collectionLabel(item.key);
              return (
                <ul key={item.key} className="list-unstyled">
                  {!hidden && (
                    <li className="cds-facets-item">
                      <a
                        href="#facet"
                        className={`cds-facets-item-link${
                          checked ? " cds-facets-item-link-checked" : ""
                        }`}
                        onClick={(e) => {
                          e.preventDefault();
                          toggleFacet(state, store, key, item.key);
                        }}
                      >
                        {label}
                        <span className="cds-facets-item-link-counter pull-right fw-b">
                          {checked ? (
                            <i className="fa fa-remove" />
                          ) : (
                            <span>{item.doc_count}</span>
                          )}
                        </span>
                      </a>
                    </li>
                  )}
                </ul>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

/** Facets of the deposit list (cds_deposit/search/facets.html). */
export function DepositSearchFacets() {
  const [state, store] = useSearch();
  if (isFirstLoad(state)) {
    return <FacetsPlaceholder count={3} />;
  }
  const aggregations = state.results.aggregations || {};
  return (
    <>
      {Object.keys(aggregations).map((key) => {
        const value = aggregations[key];
        if (!((value.buckets || []).length > 0)) {
          return null;
        }
        const values = facetValues(state.currentParams, key);
        return (
          <div key={key} className="cds-border ba mb-30 pa-10 b-r-3">
            <h2 className="text-capitalize f8 mt-5">
              <b>{String(key).replace(/_/g, " ")}</b>
            </h2>
            {value.buckets.map((item) => {
              const checked = values.indexOf(item.key) > -1;
              return (
                <ul key={item.key} className="list-unstyled">
                  <li className="cds-facets-item">
                    <a
                      href="#facet"
                      className={`cds-facets-item-link${
                        checked ? " cds-facets-item-link-checked" : ""
                      }`}
                      onClick={(e) => {
                        e.preventDefault();
                        toggleFacet(state, store, key, item.key);
                      }}
                    >
                      {key === "created_by" ? "me" : item.key}{" "}
                      <span className="cds-facets-item-link-counter pull-right fw-b">
                        {checked ? (
                          <i className="fa fa-remove" />
                        ) : (
                          <span>{item.doc_count}</span>
                        )}
                      </span>
                    </a>
                  </li>
                </ul>
              );
            })}
          </div>
        );
      })}
    </>
  );
}

const RANGE_DEFAULTS = {
  height: 70,
  name: "years",
  histogramId: "#hist",
  selectionId: "#select",
  margins: { left: 10, right: 10, top: 10, bottom: 0 },
  barColor: "#2c3e50",
  selectColor: "#3498db",
  lineColor: "#ccc",
  circleColor: "white",
  padding: 2,
};

/** ``invenio-search-range`` (cds_search_ui/range.html) */
export function SearchRange({ options: userOptions }) {
  const [state, store] = useSearch();
  const options = useRef(null);
  if (options.current === null) {
    options.current = { ...RANGE_DEFAULTS, ...userOptions };
    options.current.responsive = !userOptions.width;
  }
  const opts = options.current;
  const latest = useRef(state);
  latest.current = state;
  const aggregation = (state.results.aggregations || {})[opts.name];
  const hasBuckets = aggregation && (aggregation.buckets || []).length > 0;

  useEffect(() => {
    let active = true;

    function changeUserSelection(from, to) {
      if (!isNaN(from) && !isNaN(to)) {
        store.changeParams({ [opts.name]: from + "--" + to });
      }
    }

    function getRangeWidth() {
      const elem = document.querySelector(opts.histogramId);
      return elem ? elem.getBoundingClientRect().width : 0;
    }

    function updateRange() {
      const current = latest.current;
      if (opts.responsive) {
        opts.width = getRangeWidth() || opts.initialWidth;
      }
      if (
        current.results.aggregations &&
        current.results.aggregations[opts.name]
      ) {
        const buckets = current.results.aggregations[opts.name].buckets;
        if (buckets.length > 0) {
          const selection = current.args[opts.name];
          if (selection && selection.length > 0) {
            const args = String(selection).split("--");
            const rMin = +args[0];
            const rMax = args.length === 2 ? +args[1] : rMin;
            if (!isNaN(rMin) && !isNaN(rMax)) {
              opts.selectionRange = { min: rMin, max: rMax };
            }
          }
          loadHistogram().then(({ renderHistogram }) => {
            if (active) {
              renderHistogram(
                opts.histogramId,
                opts.selectionId,
                buckets,
                opts,
                changeUserSelection
              );
            }
          });
        }
      }
    }

    if (opts.responsive && opts.initialWidth === undefined) {
      opts.initialWidth = getRangeWidth();
    }
    if (!state.loading) {
      updateRange();
    }
    if (opts.responsive) {
      window.addEventListener("resize", updateRange);
    }
    return () => {
      active = false;
      window.removeEventListener("resize", updateRange);
    };
  }, [state.loading, state.results, store, opts]);

  const resetRangeSelection = (e) => {
    e.preventDefault();
    delete opts.selectionRange;
    store.changeParams({ [opts.name]: [] });
  };

  const selected = state.args[opts.name] && state.args[opts.name].length > 0;
  return (
    <div
      className="cds-search-facets bg-w pt-30"
      style={{ display: hasBuckets ? undefined : "none" }}
    >
      <div className="cds-border ba pa-10 b-r-3">
        <h2 className="text-capitalize f8 mt-5">
          <b>year</b>
          {selected && (
            <span className="pull-right">
              <a href="#reset" onClick={resetRangeSelection}>
                reset
              </a>
            </span>
          )}
        </h2>
        <div>
          <div
            style={{ margin: "0 auto" }}
            id={opts.histogramId.replace("#", "")}
          />
          <div
            style={{ margin: "0 auto" }}
            id={opts.selectionId.replace("#", "")}
          />
        </div>
      </div>
    </div>
  );
}

SearchRange.propTypes = { options: PropTypes.object.isRequired };

/** ``invenio-search-select-box`` (cds_search_ui/selectbox.html) */
export function SearchSelectBox({ sortKey = "sort", availableOptions }) {
  const [state, store] = useSearch();
  const options = (availableOptions && availableOptions.options) || [];

  const strip = (value) =>
    value && value.charAt(0) === "-" ? value.slice(1, value.length) : value;
  let selectedOption =
    strip(state.args[sortKey]) ||
    strip(state.sortArgs[sortKey]) ||
    (state.args[sortKey] === undefined && options.length ? null : null);
  if (!selectedOption) {
    selectedOption = options.length ? options[0].value : null;
  }
  // The template shows the first option whose properties contain the value
  const match = angularFilter(options, selectedOption)[0];
  const title = (match && match.title) || "Select";

  return (
    <Dropdown
      className="cds-select-btn text-capitalize"
      button
      basic
      icon={null}
      trigger={
        <span>
          Sort: {title} <span className="cds-caret" />
        </span>
      }
    >
      <Dropdown.Menu>
        {options.map((option) => (
          <Dropdown.Item
            key={option.value}
            text={option.title}
            onClick={() => store.setArgs({ [sortKey]: option.value })}
          />
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
}

SearchSelectBox.propTypes = {
  sortKey: PropTypes.string,
  availableOptions: PropTypes.object.isRequired,
};

/** Pages to display, like ``invenio-search-pagination``. */
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
 * ``invenio-search-pagination`` with the CDS template (``variant="cds"``,
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

/**
 * ``invenio-search-results`` rendering a template component, or its
 * placeholder while the search is loading.
 */
export function SearchResults({
  template: Template,
  placeholder: TemplatePlaceholder = null,
  ...props
}) {
  const [state] = useSearch();
  if (TemplatePlaceholder && (state.loading || isFirstLoad(state))) {
    return <TemplatePlaceholder args={state.args} />;
  }
  return <Template results={state.results} args={state.args} {...props} />;
}

SearchResults.propTypes = {
  template: PropTypes.elementType.isRequired,
  placeholder: PropTypes.elementType,
};
