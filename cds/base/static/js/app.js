/** @jsx React.DOM
 *
 * This file is part of Invenio.
 * Copyright (C) 2014 CERN.
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

// AMD format
// ----------
// define(
//     ["jquery",
//      "react",
//      "jsx!prototype/prototype",
//      "!jsx!prototype/data.json"],
//     function($, React, proto, boxes)
// {
//
// CommonJS-like format
// --------------------
define(function(require, exports, module) {
    "use strict"

    var $ = require("jquery"),
        React = require("react"),
        Proto = require("jsx!prototype/prototype"),
        boxes = require("json!prototype/data.json")


    var rows = [[]]
    var picked = [];
    while (picked.length < boxes.length) {
        var i, box;
        do {
            i = Math.floor(Math.random() * boxes.length);
        } while (picked.indexOf(i) >= 0)
        box = boxes[i]
        picked.push(i)

        if (!rows[rows.length - 1] || rows[rows.length - 1].length >= 3) {
            rows.push([])
        }
        rows[rows.length - 1].push({
            id: "b" + i,
            box: Proto[box.box](box.data)
        })
    }

    var original = $("div.websearch").before("<div id=__proto__></div>")

    var p = React.renderComponent(Proto({
            labels: {
                on: "Switch to all the collections",
                off: "Switch to your personal collections"
            },
            rows: rows,
            onToggle: function(event) {
                original.toggle();
            }
        }),
        $("#__proto__")[0])

    module.exports = {
        original: original[0],
        proto: p
    }
})
