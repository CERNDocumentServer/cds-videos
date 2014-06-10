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

    var React = require('react'),
        AdminBar = require("jsx!./admin"),
        TopBar = require("jsx!./topbar"),
        Grid = require("jsx!./grid")

    module.exports = React.createClass({
        getInitialState: function() {
            this.props.onToggle()

            var rows = [],
                swap = this.onSwap

            this.props.rows.forEach(function(row, i) {
                row.forEach(function(box, i) {
                    box.box.data.id = box.id
                    box.box.data.swap = swap
                })

                rows.push({
                    id: "r" + i,
                    boxes: row
                })
            })

            return {
                personal: true,
                admin: false,
                rows: rows
            }
        },
        onState: function(state) {
            if ("personal" in state && state.personal != this.state.personal) {
                this.props.onToggle()
            }
            this.setState(state)
        },
        /**
         * Swaping box A and box B in the list of boxes.
         */
        onSwap: function(a, b) {
            var rows = this.state.rows

            for (var i=rows.length-1; i>=0; i--) {
                for (var j=rows[i].boxes.length-1; j>=0; j--) {
                    if (rows[i].boxes[j].id === a) {
                        for (var k=rows.length-1; k>=0; k--) {
                            for (var l=rows[k].boxes.length-1; l>= 0; l--) {
                                if (rows[k].boxes[l].id === b) {
                                    var tmp = rows[i].boxes[j]
                                    rows[i].boxes.splice(j, 1, rows[k].boxes[l])
                                    rows[k].boxes.splice(l, 1, tmp)

                                    return this.setState({rows: rows})
                                }
                            }
                        }
                    }
                }
            }
        },
        render: function() {
            return (
                <div>
                    <TopBar labels={this.props.labels}
                            personal={this.state.personal}
                            admin={this.state.admin}
                            setState={this.onState}/>
                    <AdminBar personal={this.state.personal}
                              admin={this.state.admin}
                              setState={this.onState}/>
                    <Grid rows={this.state.rows}
                          personal={this.state.personal}
                          admin={this.state.admin}
                          onSwap={this.onSwap}/>
                </div>
            )
        }
    })
})
