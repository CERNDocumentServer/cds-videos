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
    var React = require("react")

    module.exports = React.createClass({
        render: function() {
            var href = this.props.href || "#",
                title = this.props.title || "Untitled"

            return (
                <div className="box-admin" onClick={this.props.onMenu}>
                    <div className="box-admin-buttons btn-group-vertical">
                        <a href={href} className="btn btn-primary">Visit “{title}”</a>
                        <button type="button" className="btn btn-default">
                            <i className="glyphicon glyphicon-move"></i> Move
                        </button>
                        <button type="button" className="btn btn-default">
                            <i className="glyphicon glyphicon-pushpin"></i> Pin
                        </button>
                        <button type="button" className="btn btn-danger">
                            <i className="glyphicon glyphicon-remove"></i> Disable
                        </button>
                    </div>
                </div>
            )
        }
    })
})
