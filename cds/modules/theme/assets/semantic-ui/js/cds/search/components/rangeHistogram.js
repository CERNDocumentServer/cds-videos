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
 * Year histogram with a brush selection, ported as is from the
 * ``invenioSearchRangeFactory`` of invenio-search-js (d3 v3), so that the
 * year facet looks and behaves exactly like before.
 */

import * as d3module from "d3";
import _cloneDeep from "lodash/cloneDeep";
import _isEqual from "lodash/isEqual";

const d3 = d3module.default || d3module;

let histSvg;
let selectorSvg;
let xScale;
let yScale;
let brush;
let selected = [];
let options;
let rangeStart;
let rangeEnd;
let previousExtent = [];
const valueToIgnore = 0.01;

function processData(data) {
  previousExtent = [];
  data.forEach((d) => {
    d.key = +d.key_as_string;
    if (options.showBarOnEmpty && d.doc_count === 0) {
      d.doc_count = valueToIgnore;
    }
    if (options.selectionRange) {
      d.selected =
        d.key >= options.selectionRange.min &&
        d.key <= options.selectionRange.max;
    } else {
      d.selected = true;
    }
  });
  const keys = data.map((e) => e.key);
  rangeStart = Math.min.apply(undefined, keys);
  rangeEnd = Math.max.apply(undefined, keys);
}

function updateBrushPosition(range, shouldSendBrushEvent) {
  range = _cloneDeep(range);
  if (range.length && range[0] === range[1]) {
    range[1] += 0.00001;
  }
  brush.extent(range);
  brush(d3.select(".brush").transition());
  if (shouldSendBrushEvent) {
    brush.event(d3.select(".brush").transition());
  }
}

function createSelector(placement, selectPlacement, onSelection) {
  if (selectorSvg) {
    selectorSvg.remove();
  }
  selectorSvg = d3
    .select(selectPlacement)
    .append("svg")
    .attr({ width: options.width, height: 35 })
    .style("fill", options.selectColor)
    .style("overflow", "visible");

  selectorSvg
    .append("line")
    .attr({ x1: 0, x2: options.width, y1: 5.5, y2: 5.5 })
    .style({ stroke: options.lineColor, "stroke-width": 3 });

  const onBrushed = function () {
    let extent = brush.extent().map(Math.round);
    if (extent.some(isNaN)) {
      extent = [rangeStart, rangeEnd];
    }
    d3.select(".brush-range.min").text(extent[0]);
    d3.select(".brush-range.max").text(extent[1]);
    selected = [];
    d3.selectAll("g.bar")
      .select("rect")
      .style("fill", function (d) {
        d.selected = d.key >= extent[0] && d.key <= extent[1];
        if (d.selected) {
          selected.push(d.key);
        }
        return d.selected ? options.selectColor : options.barColor;
      });
  };

  let initialExtent = [rangeStart, rangeEnd];
  if (options.selectionRange) {
    const minX = parseInt(xScale.domain()[0]);
    const maxX = parseInt(xScale.domain()[1]);
    const rangeMin =
      options.selectionRange.min < minX || options.selectionRange.min > maxX
        ? minX
        : options.selectionRange.min;
    const rangeMax =
      options.selectionRange.max > maxX || options.selectionRange.max < minX
        ? maxX
        : options.selectionRange.max;
    initialExtent = [rangeMin, rangeMax];
  }

  brush = d3.svg
    .brush()
    .x(xScale)
    .extent(initialExtent)
    .on("brush", onBrushed)
    .on("brushend", function () {
      let extent;
      if (selected.length === 0) {
        extent = [rangeStart, rangeEnd];
      } else {
        extent = brush.extent().map(Math.round);
        extent[0] = Math.max(extent[0], rangeStart);
        extent[1] = Math.min(extent[1], rangeEnd);
      }
      const sameRangeAsPrevious = _isEqual(previousExtent, extent);
      const shouldSendBrushEvent = !sameRangeAsPrevious;
      updateBrushPosition(extent, shouldSendBrushEvent);
      if (!sameRangeAsPrevious) {
        if (!_isEqual(initialExtent, extent)) {
          onSelection.apply(undefined, extent);
        }
        previousExtent = _cloneDeep(extent);
      }
    });

  selectorSvg
    .append("g")
    .attr("class", "brush")
    .call(brush)
    .selectAll("rect")
    .attr("y", 4)
    .attr("height", 3);

  const brushHandleGroup = selectorSvg.selectAll(".resize").append("g");
  brushHandleGroup
    .append("circle")
    .attr("r", 5)
    .attr("cx", 0)
    .attr("cy", 6)
    .style({
      "stroke-width": 2,
      stroke: options.selectColor,
      fill: options.circleColor,
    });

  brushHandleGroup
    .append("text")
    .attr("text-anchor", "middle")
    .style("transform", "rotate(-45deg) translateX(-15px)")
    .text((d, i) => parseInt(brush.extent()[i === 0 ? 1 : 0]))
    .attr("class", (d, i) => "brush-range " + (i === 0 ? "max" : "min"))
    .attr("y", 31);

  if (parseInt(initialExtent[0]) === parseInt(initialExtent[1])) {
    d3.select(".resize.e").style("display", "inline");
  }
}

/**
 * Render a histogram and a selection bar.
 *
 * @param placement {string} - The element to contain the histogram.
 * @param selectPlacement {string} - The element to contain the bar.
 * @param data {Array} - The buckets to be displayed.
 * @param userOptions {Object} - Options for rendering.
 * @param onSelection {Function} - Called with (from, to) on selection.
 */
export function renderHistogram(
  placement,
  selectPlacement,
  data,
  userOptions,
  onSelection
) {
  options = userOptions;

  if (histSvg) {
    histSvg.remove();
  }
  histSvg = d3
    .select(placement)
    .append("svg")
    .attr({ width: options.width, height: options.height });

  const group = histSvg.append("g").style("pointer-events", "all");
  const div = d3
    .select("body")
    .append("div")
    .attr("class", "range_tooltip")
    .style({
      position: "absolute",
      "text-align": "center",
      width: "40px",
      height: "18px",
      padding: "2px",
      font: "12px sans-serif",
      background: "lightblue",
      border: "0px",
      "border-radius": "8px",
      "pointer-events": "none",
      opacity: 0,
    });

  processData(data);
  const rangeDomain = d3.extent(data, (d) => d.key);
  rangeDomain[0] = rangeDomain[0] - 0.1 * data.length;
  rangeDomain[1] = rangeDomain[1] + 0.1 * data.length;

  xScale = d3.scale
    .linear()
    .domain(rangeDomain)
    .range([
      options.margins.left,
      options.width - options.margins.left - options.margins.right,
    ]);

  let barWidth = Math.min(
    10,
    (options.width -
      options.margins.left -
      options.margins.right -
      data.length * options.padding) /
      (rangeEnd - rangeStart)
  );
  barWidth = Math.max(1, barWidth);

  const maxValue = d3.max(data, (d) => d.doc_count);
  yScale = d3.scale
    .linear()
    .domain([0, maxValue])
    .range([0, options.height - options.margins.bottom]);

  const rectEnter = group
    .selectAll(".bar")
    .data(data)
    .enter()
    .append("g")
    .attr("class", "bar");

  rectEnter
    .append("rect")
    .attr("height", (d) => yScale(d.doc_count))
    .attr("width", barWidth)
    .attr("x", (d) => xScale(d.key) - barWidth / 2)
    .attr("y", (d) => yScale.range()[1] - yScale(d.doc_count))
    .style("fill", (d) =>
      d.selected ? options.selectColor : options.barColor
    );

  rectEnter
    .on("mouseenter", function (d) {
      if (d.doc_count === valueToIgnore) {
        return;
      }
      d3.select(this).style("cursor", "pointer");
      d3.select(this).style("opacity", 0.8);
      d3.select(this)
        .select("rect")
        .style(
          "fill",
          d3.rgb(d.selected ? options.selectColor : options.barColor).brighter()
        );
      div.transition().duration(200).style("opacity", 0.9);
      div
        .html(d.doc_count)
        .style("left", d3.event.pageX + "px")
        .style("top", d3.event.pageY - 28 + "px");
    })
    .on("mouseout", function (d) {
      if (d.doc_count === valueToIgnore) {
        return;
      }
      d3.select(this).style("cursor", "default");
      d3.select(this).style("opacity", 1);
      d3.select(this)
        .select("rect")
        .style("fill", d.selected ? options.selectColor : options.barColor);
      div.transition().duration(500).style("opacity", 0);
    })
    .on("click", function (d) {
      if (d.doc_count === valueToIgnore) {
        return;
      }
      div.transition().style("opacity", 0);
      updateBrushPosition([d.key, d.key], true);
      d3.select(".resize.e").style("display", "inline");
    });

  createSelector(placement, selectPlacement, onSelection);
}

