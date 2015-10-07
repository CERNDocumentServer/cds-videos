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

var calculate_interval = function(number_of_points, time_from, time_to) {
    var true_interval = (0.0 + time_to - time_from) / (0.0 + number_of_points);
    var second = 1000;
    var minute = 60*second;
    var hour = 60*minute;
    var day = 24*hour;
    var rounded_interval;
    if ( true_interval > day ) {
        rounded_interval = Math.round(true_interval / day);
        return rounded_interval + "d";
    } else if ( true_interval > hour ) {
        rounded_interval = Math.round(true_interval / hour);
        return rounded_interval + "h";
    } else if ( true_interval > minute ) {
        rounded_interval = Math.round(true_interval / minute);
        return rounded_interval + "m";
    } else if ( true_interval > second ) {
        rounded_interval = Math.round(true_interval / second);
        return rounded_interval + "s";
    } else {
        return '1s';
    }
};

define(['jquery', 'lodash', 'flot', 'time', 'datetimepicker'],
       function($, _, flot, time) {
           return { draw: function(doc_type, rec_id) {
               var now = Date.now();
               var default_time_from = now - (30*24*60*60*1000); // 30 days ago
               var default_time_to = now;
               var default_number_of_points = 50; // This is a soft maximum

               var initialise_histogram = function(selector) {

                   var plot = $.plot(selector, [temp_points], {
                       xaxis: {
                           mode: 'time'
                       },
                       series: {
                           points: { show: false },
                           lines: { show: false }
                       }
                   });
               };
               var draw_histogram = function(settings) {
                   var times_specified = ('time_from' in settings) && ('time_to' in settings);

                   var ajax_data = {};

                   if ('rec_id' in settings) {
                       ajax_data.rec_id = settings.rec_id;
                   }

                   settings.number_of_points = default_number_of_points;

                   if (times_specified) {
                       ajax_data.time_from = settings.time_from;
                       ajax_data.time_to = settings.time_to;
                   } else {
                       ajax_data.time_from = default_time_from;
                       ajax_data.time_to = default_time_to;
                   }

                   ajax_data.interval = calculate_interval(settings.number_of_points,
                                                           ajax_data.time_from,
                                                           ajax_data.time_to);

                   $("<div id='tooltip'></div>").css({
                       position: "absolute",
                       display: "none",
                       border: "1px solid #fdd",
                       padding: "2px",
                       "background-color": "#fee",
                       opacity: 0.80
                   }).appendTo("body");

                   $.ajax(settings.data_url, {data: ajax_data})
                       .done(function(data) {
                           $(settings.selector)[0].innerHTML = '';
                           $('#refresh_button')[0].disabled = false;
                           var points = _.map(data[1], function(raw_point) {
                               return [raw_point.key, raw_point.doc_count];
                           });
                           $.plot(settings.selector, [points], {
                               xaxis: {
                                   mode: "time"
                               },
                               series: {
                                   points: { show: true },
                                   lines: {show: true}
                               },
                               grid: {
                                   hoverable: true
                               }
                           });
                           $(settings.selector).bind('plothover', function (event, pos, item) {
                               if (item) {
                                   var index = item.dataIndex;
                                   var date = new Date();
                                   date.setTime(item.series.data[index][0]);
                                   var key = date.toDateString() + ' ' + date.toTimeString();
                                   var y = item.datapoint[1];
                                   $('#tooltip').html(y + ' @ ' + key)
                                       .css({top: item.pageY+5, left: item.pageX+5})
                                       .fadeIn(200);
                               }
                               else {
                                   $('#tooltip').hide();
                               }
                           });
                       });

               };

               var refreshTimeline = function() {
                   var settings = {
                       data_url: '/statistics/api/' + doc_type + '/histogram',
                       selector: '#placeholder',
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

                   if ( !isNaN(time_from) && !isNaN(time_to) && !time_from_empty_p && !time_to_empty_p ) {
                       settings.time_from = time_from;
                       settings.time_to = time_to;
                   }

                   $('#refresh_button')[0].disabled = true;
                   draw_histogram(settings);
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
                   refreshTimeline();
               });
               refreshTimeline();
           }};
       });