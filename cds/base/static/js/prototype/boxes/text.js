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

    var $ = require("jquery"),
        React = require("react"),
        Admin = require("jsx!./admin")

    module.exports = React.createClass({
        getInitialState: function() {
            return {edit: false}
        },
        onMenu: function(event) {
            this.setState({edit: !this.state.edit})
            return false
        },
        render: function() {
            var header = $.extend({"href": "#"}, this.props.header),
                footer = $.extend({"label": "more {this.props.header.title}", "href": header.href},
                                  this.props.footer),
                edit = ""

            var className = "box-body";
            if (!("wrap" in this.props) || this.props.wrap) {
                className += " wrap";
            }
            if (this.state.edit) {
                edit = <Admin title={header.title} href={header.href} onMenu={this.onMenu}/>
            }

            return (
                <article className="box">
                    <header>
                        <h2>
                            <a href={header.href} onClick={this.onMenu}>
                                {header.title}
                            </a>
                        </h2>
                    </header>
                    <div className={className} dangerouslySetInnerHTML={{__html: this.props.body}}/>
                    <footer>
                        <p>
                            <a href="{footer.href}">{footer.label} »</a>
                        </p>
                    </footer>
                    {edit}
                </article>
            )
        }
    })
})
