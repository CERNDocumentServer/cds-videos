/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Facets of the search page and of the list of uploads. */

import React from "react";

import { collectionLabel } from "@js/cds/shared/utils/text";
import { isoToLanguage } from "@js/cds/shared/utils/languages";

import { FacetsPlaceholder } from "./Placeholders";
import { useSearch } from "../hooks";
import { isFirstLoad } from "./SearchStatus";

function facetValues(currentParams, key) {
  const value = currentParams[key];
  if (value === undefined) return [];
  return typeof value === "string" ? [value] : value;
}

/** Toggle a facet value. */
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

/** Facets of the search page. */
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

/** Facets of the list of uploads. */
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
