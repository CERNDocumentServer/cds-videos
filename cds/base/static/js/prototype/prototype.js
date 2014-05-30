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
            return {personal: true}
        },
        handleClick: function() {
            this.setState({personal: !this.state.personal})
            return false
        },
        render: function() {
            var label = this.state.personal ?
                this.props.labels.on :
                this.props.labels.off

            if (this.state.personal) {
                this.props.original.hide();
                this.props.related.show();
                $(".hamburger").show();
            } else {
                this.props.original.show();
                this.props.related.hide();
                $(".hamburger").hide();
            }

            return (
                <p className={this.props.className}>
                    <a href="#" onClick={this.handleClick}>{label}</a>
                </p>
            )
        }
    })

    var Hamburger = React.createClass({
        getInitialState: function() {
            return {active: false}
        },
        handleClick: function() {
            alert("admin mode")
            return false
        },
        render: function() {
            var className = this.props.className + " hamburger text-right"
            return (
                <p className={className}>
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
                            original={this.props.original}
                            related={this.props.related}
                            className={className} />
                    <Hamburger className={className} />
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
    exports.Grid = require("jsx!prototype/grid.js").Grid,
    exports.Row = require("jsx!prototype/row.js").Row,
    exports.Box = require("jsx!prototype/boxes/text.js").Box
    exports.PictureBox = require("jsx!prototype/boxes/picture.js").Box
})
