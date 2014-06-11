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
        Grid = require("jsx!./grid"),
        _ = require("underscore")

    module.exports = React.createClass({
        getInitialState: function() {
            this.props.onToggle()

            return {
                personal: true,
                admin: false,
                rows: 1
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
            var collection = this.props.collection,
                boxA = collection.findWhere({id: a}),
                boxB = collection.findWhere({id: b}),
                positionA = boxA.get("position")

            boxA.set("position", boxB.get("position"))
            boxB.set("position", positionA)

            boxA.save()
            boxB.save()
            collection.sort()
            this.setProps({collection: collection})
        },
        render: function() {
            var boxes = [],
                swap = this.onSwap

            this.props.collection.forEach(function(box) {
                box.set("data", _.extend({swap: swap}, box.get("data")))
                boxes.push(box)
            })

            return (
                <div>
                    <TopBar labels={this.props.labels}
                            personal={this.state.personal}
                            admin={this.state.admin}
                            setState={this.onState}/>
                    <AdminBar personal={this.state.personal}
                              admin={this.state.admin}
                              setState={this.onState}/>
                    <Grid boxes={boxes}
                          plus={this.state.plus}
                          personal={this.state.personal}
                          admin={this.state.admin}
                          onPlus={this.onPlus}
                          onSwap={this.onSwap}/>
                </div>
            )
        }
    })
})
