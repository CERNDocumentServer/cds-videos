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

    var _ = require("underscore"),
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
        onMoveUp: function(event) {
            this.props.swap(null, this.props.id)
            event.preventDefault()
        },
        onMoveDown: function(event) {
            this.props.swap(this.props.id, null)
            event.preventDefault()
        },
        onDisable: function(box) {
            this.props.onDisable(box)
        },
        onDragOver: function(event) {
            event.preventDefault()
        },
        onDragStart: function(event) {
            event.dataTransfer.setData("text", this.props.id)
        },
        onDrop: function(event) {
            event.preventDefault();
            this.props.swap(this.props.id, event.dataTransfer.getData("text"))
        },
        onTouchStart: function(event) {
            // don't break multi-touch
            if (event.touches.length == 1) {
                // double tap in under 300ms
                if (this.timer) {
                    this.setState({edit: !this.state.edit})
                    clearTimeout(this.timer)
                    this.timer = 0
                } else {
                    this.timer = setTimeout(_.bind(function(){
                        this.timer = 0
                    }, this), 300)
                }
            }
        },
        onTouchEnd: function(event) {
        },
        render: function() {
            var header = _.extend({"href": "#"}, this.props.header),
                footer = _.extend({"label": "more {this.props.header.title}", "href": header.href},
                                  this.props.footer),
                edit = ""

            var className = "box-body";
            if (!("wrap" in this.props) || this.props.wrap) {
                className += " wrap";
            }
            if (this.state.edit) {
                edit = <Admin id={this.props.id}
                              title={header.title}
                              href={header.href}
                              labels={this.props.labels}
                              onMenu={this.onMenu}
                              onMoveUp={this.onMoveUp}
                              onMoveDown={this.onMoveDown}
                              onDisable={this.props.disable}/>
            }

            return (
                <article className="box"
                         draggable="true" onDragStart={this.onDragStart} onDrop={this.onDrop} onDragOver={this.onDragOver}
                         onTouchStart={this.onTouchStart} onTouchEnd={this.onTouchEnd}>
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
                            <a href={footer.href}>{footer.label} »</a>
                        </p>
                    </footer>
                    {edit}
                </article>
            )
        }
    })
})
