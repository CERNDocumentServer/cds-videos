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
        React = require("react")

    module.exports = React.createClass({
        onRow: function(event) {
            alert("row to show: " + $(event.target).html())
        },
        onEnable: function(event) {
            var target = $(event.target).closest("a");
            if (target.length) {
                console.info("enable back:" + target.text());
                this.props.onEnable(target.data("id"))
            }
            return false
        },
        onCancel: function() {
            console.log("cancel")
            this.onClose()
        },
        onSave: function() {
            console.log("save and close")
            this.onClose()
        },
        onClose: function() {
            this.props.setState({admin: false})
        },
        render: function() {
            var style = {display: this.props.personal && this.props.admin ? "block": "none"},
                disabledBoxes = <p>All the boxes are enabled.</p>

            if (this.props.boxes.length) {
                disabledBoxes = <ul onClick={this.onEnable}>
                    {this.props.boxes.map(function(box){
                        var data = box.get("data")
                        return (
                            <li key={box.get("id")}>
                                <a href={data.header.href} data-id={box.get("id")}>
                                    <i className="glyphicon glyphicon-remove"></i>
                                    {' '}{data.header.title}
                                </a>
                            </li>
                        )
                    })}
                </ul>
            }

            /*
                        <p className="col-md-6 text-right">
                            <button type="button" className="btn btn-default" onClick={this.onCancel}>Cancel</button>
                        </p>
                        <p className="col-md-6">
                            <button type="button" className="btn btn-primary" onClick={this.onSave}>Save and close</button>
                        </p>
            */
            return (
                <div className="prototype-admin" style={style}>
                    <div className="row">
                        <div className="col-md-6 text-right">
                            <p className="box-label">Visible boxes by default</p>
                        </div>
                        <div className="col-md-6">
                            <div className="btn-group" onClick={this.onRow}>
                                <button type="button" className="btn btn-primary">3</button>
                                <button type="button" className="btn btn-default">6</button>
                                <button type="button" className="btn btn-default">9</button>
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <div className="col-md-6 text-right">
                            <p className="box-label">Disabled boxes</p>
                            <p>
                                By removing some of this list,<br/>
                                they may appear again<br/>
                                on your homepage.
                            </p>
                        </div>
                        <div className="col-md-6">
                            {disabledBoxes}
                        </div>
                    </div>
                    <div className="row">
                        <p className="col-md-6 text-right">{' '}</p>
                        <p className="col-md-6">
                            <button type="button" className="btn btn-primary" onClick={this.onSave}>Close</button>
                        </p>
                    </div>
                </div>
            )
        }
    })
})
