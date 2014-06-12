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
        onEnable: function(a) {
            var collection = this.props.collection,
                boxA = collection.findWhere({id: a}),
                minPosition = collection.at(0).get("position")

            boxA.set("disabled", false)
            boxA.set("position", minPosition - 1)
            boxA.save()
            collection.sort()
            this.setProps({collection: collection})
        },
        onDisable: function(a) {
            var collection = this.props.collection,
                boxA = collection.findWhere({id: a})

            boxA.set("disabled", true)
            boxA.save()
            this.setProps({collection: collection})
        },
        render: function() {
            var boxes = [],
                swap = this.onSwap,
                disable = this.onDisable

            this.props.collection.enabled().forEach(function(box) {
                box.set("data", _.extend({swap: swap, disable: disable},
                                         box.get("data")))
                boxes.push(box)
            })

            return (
                <div>
                    <TopBar labels={this.props.labels}
                            personal={this.state.personal}
                            admin={this.state.admin}
                            setState={this.onState}/>
                    <AdminBar boxes={this.props.collection.disabled()}
                              personal={this.state.personal}
                              admin={this.state.admin}
                              setState={this.onState}
                              onEnable={this.onEnable}/>
                    <Grid boxes={boxes}
                          plus={this.state.plus}
                          personal={this.state.personal}
                          admin={this.state.admin}
                          onPlus={this.onPlus}/>
                </div>
            )
        }
    })
})
