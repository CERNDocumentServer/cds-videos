/*
 * This file is part of CDS.
 * Copyright (C) 2026 CERN.
 *
 * CDS is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 */

/** Year range facet with its histogram (d3 loads with the first one). */

import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";

import { useSearch } from "../hooks";

// The year histogram draws with d3 (about 150 KB): load it with the first
// year facet only, instead of on every page that shows search results
let histogram;

function loadHistogram() {
  histogram = histogram || import("./rangeHistogram");
  return histogram;
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
