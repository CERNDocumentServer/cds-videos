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
    "use strict";

    var $ = require("jquery"),
        _ = require("underscore"),
        React = require("react"),
        Boxes = {
            Box: require('jsx!../boxes/text'),
            PictureBox: require('jsx!../boxes/picture')
        }

    module.exports = React.createClass({
        getInitialState: function() {
            return {
                "box": null
            }
        },
        onEnable: function(event) {
            var target = $(event.target).closest("a")
            if (target.length) {
                if (this.state.box === target.data("id")) {
                    this.setState({"box": null})
                    this.props.onEnable(target.data("id"))
                } else {
                    this.setState({"box": target.data("id")})
                }
            } else {
                this.setState({"box": null})
            }
            return false
        },
        onDisable: function(event) {
            this.props.onDisable(event.dataTransfer.getData("text"))
            event.preventDefault()
        },
        onDragOver: function(event) {
            event.preventDefault()
        },
        // Swap acts as disabling here as it's put on the trashbin.
        onSwap: function(a, b) {
            this.setState({"box": null})
            this.props.onDisable(b)
        },
        render: function() {
            var disabledBoxes = <p>All the boxes are enabled.</p>,
                box = <article onDragOver={this.onDragOver} onDrop={this.onDisable} className="box box-drop">
                        <p>
                            <i className="glyphicon glyphicon-trash"></i>
                        </p>
                    </article>,
                disabled = this.props.collection.disabled(),
                found = false

            if (disabled.length) {
                //box = <p>&larr; Select a collection to preview it.</p>,
                disabledBoxes = <ul className="nav nav-stacked">
                        {disabled.map(_.bind(function(box){
                            var data = box.get("data"),
                                glyphicon = "",
                                className = ""
                            if (box.get("id") == this.state.box) {
                                found = true
                                className = "active"
                                glyphicon = <span className="pull-right">
                                        <i className="glyphicon glyphicon-plus"></i>
                                    </span>
                            }
                            return (
                                <li key={box.get("id")} className={className}>
                                    <a href={data.header.href} data-id={box.get("id")}>
                                        {glyphicon}{' '}{data.header.title}
                                    </a>
                                </li>
                            )
                        }, this))}
                    </ul>
            }

            if (this.state.box && found) {
                var b = this.props.collection.findWhere({id: this.state.box})
                box = Boxes[b.get("box")](_.extend({onSwap: this.onSwap},
                                                   b.get("data")))
            }

            return (
                <div className={this.props.className} id={this.props.id}>
                    <div className="col-sm-8" onClick={this.onEnable}>
                        <h4>Disabled collections</h4>
                    </div>
                    <div className="col-sm-4" onClick={this.onEnable}>
                        {disabledBoxes}
                    </div>
                    <div className="col-sm-4">
                        {box}
                    </div>
                </div>
            )
        }
    })
})
