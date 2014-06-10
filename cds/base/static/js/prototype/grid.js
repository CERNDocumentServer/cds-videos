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
                rows = this.props.rows,
                style = {},
                stylePlus = {}

            if (!this.props.personal) {
                style.display = "none"
            }

            if (show >= this.props.rows.length - 1) {
                stylePlus.display = "none"
            }

            return (
                <div className="grid" style={style}>
                    {rows.map(function(row, index) {
                        var style = {}

                        if (index > show) {
                            style.display = "none"
                        }
                        return (
                            <div className="row" key={row.id} style={style}>
                                {row.boxes.map(function(box) {
                                    console.log(box)
                                    console.log(box.box)
                                    var comp = Boxes[box.box.box](box.box.data)
                                    return (
                                        <div className="col-md-4" key={box.id}>
                                            {comp}
                                        </div>
                                    )
                                })}
                            </div>
                        )
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
