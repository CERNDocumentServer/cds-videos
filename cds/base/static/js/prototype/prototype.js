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
//define(["jquery", "react"], function($, React) {
// CommonJS format
define(function(require, exports, module) {
    "use strict"

    var $ = require('jquery'),
        React = require('react')

    var AdminBar = React.createClass({
        onRow: function() {
            alert("row <todo>")
        },
        onEnable: function() {
            alert("enable back <todo>")
            return false
        },
        onCancel: function() {
            alert("cancel")
        },
        onSave: function() {
            alert("save")
        },
        render: function() {
            var style = {display: this.props.personal && this.props.admin ? "block": "none"}
            return (
                <div className="prototype-admin" style={style}>
                    <div className="row">
                        <p className="col-md-6 text-right">
                            Visible boxes by default
                        </p>
                        <div className="col-md-6">
                            <div className="btn-group" onClick={this.onRow}>
                                <button type="button" className="btn btn-primary">3</button>
                                <button type="button" className="btn btn-default">6</button>
                                <button type="button" className="btn btn-default">9</button>
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <p className="col-md-6 text-right">
                            Disabled boxes
                        </p>
                        <div className="col-md-6">
                            <ul onClick={this.onEnable}>
                                <li><a href="#">
                                    <i className="glyphicon glyphicon-remove"></i> CDS Meetings
                                </a></li>
                                <li><a href="#">
                                    <i className="glyphicon glyphicon-remove"></i> Your Messages
                                </a></li>
                                <li><a href="#">
                                    <i className="glyphicon glyphicon-remove"></i> Your Alerts
                                </a></li>
                                <li><a href="#">
                                    <i className="glyphicon glyphicon-remove"></i> LHC
                                </a></li>
                                <li><a href="#">
                                    <i className="glyphicon glyphicon-remove"></i> Presentations
                                </a></li>
                            </ul>
                        </div>
                    </div>
                    <div className="row">
                        <p className="col-md-6 text-right">
                            <button type="button" className="btn btn-default" onClick={this.onCancel}>Cancel</button>
                        </p>
                        <p className="col-md-6">
                            <button type="button" className="btn btn-primary" onClick={this.onSave}>Save and close</button>
                        </p>
                    </div>
                </div>
            )
        }
    })

    var Switch = React.createClass({
        getInitialState: function() {
            return {personal: this.props.personal || true}
        },
        handleClick: function() {
            $(document).triggerHandler(this.props.eventName, [!this.state.personal])
            this.setState({personal: !this.state.personal})
            return false
        },
        render: function() {
            var label = this.props.personal ?
                this.props.labels.on :
                this.props.labels.off

            return (
                <p className={this.props.className}>
                    <a href="#" onClick={this.handleClick}>{label}</a>
                </p>
            )
        }
    })

    var Hamburger = React.createClass({
        getInitialState: function() {
            return {admin: this.props.admin || false}
        },
        handleClick: function() {
            $(document).triggerHandler(this.props.eventName, [!this.state.admin])
            this.setState({admin: !this.state.admin})
            return false
        },
        render: function() {
            var className = this.props.className + " hamburger text-right"
            var style = {};
            if (!this.props.personal) {
                style.display = "none"
            }
            return (
                <p className={className} style={style}>
                    <a href="#" onClick={this.handleClick}>
                        <i className="glyphicon glyphicon-th"></i>
                    </a>
                </p>
            )
        }
    })

    var TopBar = React.createClass({
        render: function() {
            var className = "col-md-6"
            return (
                <div className="row">
                    <Switch labels={this.props.labels}
                            personal={this.props.personal}
                            eventName={this.props.eventsName.switch}
                            className={className} />
                    <Hamburger className={className}
                               eventName={this.props.eventsName.admin}
                               personal={this.props.personal} />
                </div>
            )
        }
    })

    // AMD format
    //return {
    //    Proto: Proto,
    //    Switch: Switch
    //};
    // CommonJS format
    exports.TopBar = TopBar
    exports.AdminBar = AdminBar
    exports.Grid = require("jsx!prototype/grid.js")
    exports.Row = require("jsx!prototype/row.js")
    exports.Box = require("jsx!prototype/boxes/text.js")
    exports.PictureBox = require("jsx!prototype/boxes/picture.js")
})
