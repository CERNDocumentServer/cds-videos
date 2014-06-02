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
    var React = require("react");

    module.exports = React.createClass({
        onClose: function() {
            confirm('Closing "' + this.props.title + '"?')
            return false
        },
        render: function() {
            var href = this.props.href || "#",
                more = this.props.more || href,
                footer = this.props.footer || "more {this.props.title}",
                title = this.props.title,
                style = {background: "url(" + this.props.img + ") 50% 50%",
                         minHeight: "330px"},
                subtitle

            if (this.props.subtitle) {
                subtitle = <p>{this.props.subtitle}</p>
            }

            return (
                <article className="box box-picture" style={style}>
                    <p className="box-close">
                        <a href="#" onClick={this.onClose}>
                            <i className="glyphicon glyphicon-remove"></i>
                        </a>
                    </p>
                    <header>
                        <h2>
                            <a href={href}>{title}</a>
                        </h2>
                        {subtitle}
                    </header>
                    <div className="box-body" dangerouslySetInnerHTML={{__html: this.props.body}}/>
                    <footer>
                        <p>
                            <a href="{more}">{footer} »</a>
                        </p>
                    </footer>
                </article>
            )
        }
    })
})
