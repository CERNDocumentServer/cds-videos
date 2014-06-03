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
        handleClick: function() {
            $(document).triggerHandler(this.props.eventName, [!this.props.admin])
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
                               admin={this.props.admin}
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
    exports.AdminBar = require("jsx!./admin")
    exports.Grid = require("jsx!./grid")
    exports.Row = require("jsx!./row")
    exports.Box = require("jsx!./boxes/text")
    exports.PictureBox = require("jsx!./boxes/picture")
})
