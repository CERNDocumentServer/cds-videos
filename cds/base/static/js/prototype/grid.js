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

    var React = require('react')

    var Grid = React.createClass({
        onPlus: function() {
            alert("+1!")
            return false
        },
        render: function() {
            var rows = this.props.rows
            return (
                <div className="grid">
                    {rows.map(function(row) {
                        return (
                            <div key={row.id}>
                                {row.row}
                            </div>
                        )
                    })}
                    <div className="row">
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

    exports.Grid = Grid
})
