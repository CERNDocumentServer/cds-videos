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

define(["react"], function(React) {
    var Text = React.createClass({
        onClose: function() {
            alert("close")
        },
        render: function() {
            return (
                <article className="box">
                    <p className="box-close">
                        <a href="#" onClick={this.onClose}>
                            <i class="glyphicon glyphicon-remove"></i>
                        </a>
                    </p>
                    <header>
                        <h2>
                            <a href="#">
                                {this.props.title}
                            </a>
                        </h2>
                        <p>{this.props.subtitle}</p>
                    </header>
                    <div class="box-body">
                        {this.props.body}
                    </div>
                    <footer>
                        <p>
                            <a href="#">go to {this.props.title} »</a>
                        </p>
                    </footer>
                </article>
            )
        }
    })

    return {Box: Text}
})
