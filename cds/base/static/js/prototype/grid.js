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
        Boxes = {
            Box: require('jsx!./boxes/text'),
            PictureBox: require('jsx!./boxes/picture')
        }

    module.exports = React.createClass({
        getInitialState: function() {
            return {
                row: this.props.row || 0
            }
        },
        onPlus: function() {
            this.setState({row: this.state.row + 1})
            return false
        },
        render: function() {
            var show = this.state.row,
                boxes = this.props.boxes,
                rows = [],
                style = {},
                stylePlus = {}

            if (!this.props.personal) {
                return (<div />)
            }

            if (show >= Math.floor(boxes.length / 3)) {
                stylePlus.display = "none"
            }

            for (var i=0; i < boxes.length ; i += 3) {
                rows.push([boxes[i], boxes[i+1], boxes[i+2]])
            }

            return (
                <div className="grid">
                    {rows.map(function(row, index) {
                        if (index <= show) {
                            var key = "r" + index
                            return (
                                <div className="row" key={key}>
                                    {row.map(function(box) {
                                        if (box) {
                                            var comp = Boxes[box.get("box")](box.get("data"))
                                            return (
                                                <div className="col-md-4" key={box.id}>
                                                    {comp}
                                                </div>
                                            )
                                        }
                                    })}
                                </div>
                            )
                        }
                    })}
                    <div className="row" style={stylePlus}>
                        <p className="plus">
                            <a href="#" onClick={this.onPlus}>
                                <i className="glyphicon glyphicon-plus"></i>
                            </a>
                        </p>
                    </div>
                </div>
            )
        }
    })
})
