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
        onSearch: function(event) {
            var q = $(event.target).find("input[name=q]")
            console.log(q.val())
            alert("TODO: " + q.val())
            event.preventDefault()
        },
        render: function() {
            var hide = {"display": "none"}
            return (
                <div className={this.props.className} id={this.props.id}>
                    <div className="col-sm-8">
                        <h4>Find a collection</h4>
                    </div>
                    <form method="POST" action="#" onSubmit={this.onSearch}>
                    <div className="col-sm-4">
                        <div className="input-group">
                            <span className="input-group-addon">
                                <i className="glyphicon glyphicon-search"></i>
                            </span>
                            <input type="search" id="prototype-admin-search" name="q" className="form-control" placeholder="collection name" />
                        </div>
                    </div>
                    <div className="col-sm-4">
                        <p>
                            <button type="button" className="btn btn-default">Search</button>
                        </p>
                    </div>
                    </form>
                    <div className="col-sm-8" style={hide}>
                        <p>20 matches found for <em>ATLAS</em>.</p>
                    </div>
                    <div className="col-sm-4 clearfix" style={hide}>
                        <ul className="nav nav-stacked">
                            <li className="active"><a href="#">
                                <strong>ATLAS eNews</strong>
                            </a></li>
                            <li><a href="#">
                                ATLAS collaboration (Archives)
                            </a></li>
                            <li><a href="#">
                                ATLAS Videos
                            </a></li>
                            <li><a href="#">
                                ATLAS Theses
                            </a></li>
                            <li><a href="#">
                                ATLAS Scientific
                            </a></li>
                        </ul>
                    </div>
                    <div className="col-sm-4" style={hide}>
                        <article className="box">
                            <header><h2>ATLAS eNews</h2></header>
                            <div className="box-body wrap">
                                <h3>Box preview</h3>
                                <p>TODO</p>
                            </div>
                            <footer>
                                <p>... »</p>
                            </footer>
                        </article>
                    </div>
                </div>
            )
        }
    })
})
