/*
 * This file is part of Invenio.
 * Copyright (C) 2015 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

// TODO - wyjebac zbedne rzeczy

define(function (require) {

  'use strict';

  /**
   * Module dependencies
   */

  var _ = require('vendors/lodash/lodash');
  var d3 = require('d3');
  var elasticsearch = require('elasticsearch');

  /**
   * Module exports
   */

  return initialize;

  /**
   * Module function
   */

  var client = new elasticsearch.Client({
    host: 'localhost: 9200',
    log: 'trace'
  });


  function initialize() {
    // TODO get real stats
    var days = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]
    var frequencyGenerator = function(){
      // Return random value from 1-15, for fun now
      return Math.floor(Math.random() * 15);
    }
    var frequency = []
    for(var i=1; i <= 18; i++) {
      frequency.push(frequencyGenerator())
    }

    // Display stats using d3
    var margin = {top: 20, right: 20, bottom: 30, left: 40},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

    var x = d3.scale.ordinal()
        .rangeRoundBands([0, width], .1);

    var y = d3.scale.linear()
        .range([height, 0]);

    var xAxis = d3.svg.axis()
        .scale(x)
        .orient("bottom");

    var yAxis = d3.svg.axis()
        .scale(y)
        .orient("left")

    var svg = d3.select(".histogram").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    x.domain(days);
    y.domain([0, d3.max(frequency)]);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)

    svg.selectAll(".bar")
        .data(frequency)
      .enter().append("rect")
        .attr("class", "bar")
        .attr("x", function(d, i) { return x(i + 1); })
        .attr("width", x.rangeBand())
        .attr("y", function(d) { return y(d); })
        .attr("height", function(d) { return height - y(d); });
  }
});
