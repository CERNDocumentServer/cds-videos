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

// Here we draw histogram of page views
define(['jquery', 'd3', 'datetimepicker'], function($, Chart) {
  return { draw: function(event, field, rec_id) {
    var now = Date.now();
    var default_time_from = now - (30*24*60*60*1000); // 30 days ago
    var default_time_to = now;

    var draw_histogram = function(settings) {
      return function() {
        var ajax_data = {
          field: settings.field
        };

        if ('rec_id' in settings) {
          ajax_data.rec_id = settings.rec_id;
        }

        if ( ('time_from' in settings) && ('time_to' in settings) ) {
          ajax_data.time_from = settings.time_from;
          ajax_data.time_to = settings.time_to;
        }

        console.log(ajax_data)
        $.ajax(settings.data_url, {data: ajax_data})
          .done(function(data) {

            // Display some elements
            $('#placeholder').css('display', 'none');
            $('#refresh_button')[0].disabled = false;

            var processed_data = [];
            var total = data[0];
            var total_in_buckets = 0;
            for (var i = 0; i < data[1].length; i++) {
                var value = data[1][i]['doc_count'];
                var percentage = (100 * value)/(total + 0.0);
                var label;
                if (data[1][i].hasOwnProperty('key_as_string')) {
                    label = data[1][i]['key_as_string'];
                }
                else {
                    label = data[1][i]['key'] + '';
                }
                label += ': ' + Math.round(percentage) + '%';
                total_in_buckets += value
                processed_data.push({
                    value: value,
                    label: label,
                    color: colors[i % colors.length]
                });
            }
            var other_value = (total - total_in_buckets)
            var other_percentage = (100 * other_value)/(total + 0.0);
            processed_data.push({
                value: other_value,
                label: 'Other: ' + Math.round(other_percentage) + '%',
                color: '#AAAAAA'
            });

            console.log("Processed data:")
            console.log(processed_data)

            // TODO display this data
            // var days = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]
            // var frequencyGenerator = function(){
            //     // Return random value from 1-15, for fun now
            //     return Math.floor(Math.random() * 15);
            // }
            // var frequency = []
            // for(var i=1; i <= 18; i++) {
            //     frequency.push(frequencyGenerator())
            // }

            // // Display stats using d3
            // var margin = {top: 20, right: 20, bottom: 30, left: 40},
            //   width = 960 - margin.left - margin.right,
            //   height = 500 - margin.top - margin.bottom;

            // var x = d3.scale.ordinal()
            //   .rangeRoundBands([0, width], .1);

            // var y = d3.scale.linear()
            //   .range([height, 0]);

            // var xAxis = d3.svg.axis()
            //   .scale(x)
            //   .orient("bottom");

            // var yAxis = d3.svg.axis()
            //   .scale(y)
            //   .orient("left")

            // var svg = d3.select(".histogram").append("svg")
            //   .attr("width", width + margin.left + margin.right)
            //   .attr("height", height + margin.top + margin.bottom)
            // .append("g")
            //   .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            // x.domain(days);
            // y.domain([0, d3.max(frequency)]);

            // svg.append("g")
            //   .attr("class", "x axis")
            //   .attr("transform", "translate(0," + height + ")")
            //   .call(xAxis);

            // svg.append("g")
            //   .attr("class", "y axis")
            //   .call(yAxis)

            // svg.selectAll(".bar")
            //   .data(frequency)
            // .enter().append("rect")
            //   .attr("class", "bar")
            //   .attr("x", function(d, i) { return x(i + 1); })
            //   .attr("width", x.rangeBand())
            //   .attr("y", function(d) { return y(d); })
            //   .attr("height", function(d) { return height - y(d); });
            // }


                // $('#placeholder').css('display', 'none');
                // $('#refresh_button')[0].disabled = false;

                // var colors = ["#7EB26D", "#EAB839", "#6ED0E0", "#EF843C", "#E24D42", "#1F78C1", "#BA43A9", "#705DA0", "#508642", "#CBA300"];

                // var processed_data = [];
                // var total = data[0];
                // var total_in_buckets = 0;
                // for (var i = 0; i < data[1].length; i++) {
                //     var value = data[1][i]['doc_count'];
                //     var percentage = (100 * value)/(total + 0.0);
                //     var label;
                //     if (data[1][i].hasOwnProperty('key_as_string')) {
                //         label = data[1][i]['key_as_string'];
                //     }
                //     else {
                //         label = data[1][i]['key'] + '';
                //     }
                //     label += ': ' + Math.round(percentage) + '%';
                //     total_in_buckets += value
                //     processed_data.push({
                //         value: value,
                //         label: label,
                //         color: colors[i % colors.length]
                //     });
                // }
                // var other_value = (total - total_in_buckets)
                // var other_percentage = (100 * other_value)/(total + 0.0);
                // processed_data.push({
                //     value: other_value,
                //     label: 'Other: ' + Math.round(other_percentage) + '%',
                //     color: '#AAAAAA'
                // });
                // var ctx = $('#chart')[0].getContext("2d");
                // var chart = new Chart(ctx).Pie(processed_data, {});
          });
        // END of .done
      };
    };

  var refreshPie = function() {
    var settings = {
      data_url: '/statistics/api/' + event + '/terms',
      field: field,
      rec_id: rec_id
    };

    var time_from_empty_p = $('#time_from')[0].value === '';
    var time_to_empty_p = $('#time_to')[0].value === '';

    if ( !time_from_empty_p && !time_to_empty_p ) {
      var time_from = $('#time_from').data("DateTimePicker").date().valueOf();
      var time_to = $('#time_to').data("DateTimePicker").date().valueOf();
      if ( !isNaN(time_from) && !isNaN(time_to) ) {
        settings.time_from = time_from;
        settings.time_to = time_to;
      }
    }

    $('#refresh_button')[0].disabled = true;

    $(draw_histogram(settings));
  };

    // Date picker
    $('#time_from').datetimepicker({
        sideBySide: true,
        format: 'YYYY-MM-DD HH:mm'
    });
    $('#time_to').datetimepicker({
        sideBySide: true,
        format: 'YYYY-MM-DD HH:mm'
    });
    $('#refresh_button').bind('click', function() {
        refreshPie();
    });
    refreshPie();
  }};
});