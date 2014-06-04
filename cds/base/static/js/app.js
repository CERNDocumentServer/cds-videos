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

define(function(require, exports, module) {
    "use strict"

    var $ = require("jquery"),
        React = require("react"),
        proto = require("jsx!prototype/prototype"),
        boxes = require("json!prototype/data.json")

    var rows = [[]],
        grid = {rows: [], personal: true}

    // Ordered boxes
    //$.each(boxes, function(i, box) {
    // Randomly sorted boxes
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
            box: proto[box.box](box.data)
        })
    //})
    }
    $.each(rows, function(i, row) {
        grid.rows.push({
            id: "r" + i,
            row: proto.Row({boxes: row})
        })
    })

    var original = $("div.websearch")
        .before("<div id=prototype-topbar></div>")
        .before("<div id=prototype-adminbar></div>")
        .before("<div id=prototype-row></div>")

    var topBar = React.renderComponent(proto.TopBar({
                labels: {
                    on: "Switch to all the collections",
                    off: "Switch to your personal collections"
                },
                personal: "true",
                eventsName: {
                    "switch": "prototype:switch",
                    "admin": "prototype:admin"
                }
            }),
            $("#prototype-topbar")[0])

    var adminBar = React.renderComponent(
            proto.AdminBar({
                admin: false,
                eventName: "prototype:admin"
            }),
            $("#prototype-adminbar")[0])

    var grid = React.renderComponent(
            proto.Grid(grid),
            $("#prototype-row")[0])

    $(document)
        .on("prototype:switch", function(event, show) {
            var props = {personal: show}
            adminBar.setProps(props)
            topBar.setProps(props)
            grid.setProps(props)

            if (show) {
                original.hide()
            } else {
                original.show()
            }
        })
        .on("prototype:admin", function(event, show) {
            var props = {admin: show}
            topBar.setProps(props)
            adminBar.setProps(props)
        })
        .trigger("prototype:switch", [true])
        .trigger("prototype:admin", [false])

    module.exports = {
        original: original[0],
        topBar: topBar,
        adminBar: adminBar,
        grid: grid
    }
})
