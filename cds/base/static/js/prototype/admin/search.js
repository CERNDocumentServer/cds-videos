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
        BoxList = require("jsx!./boxlist"),
        Boxes = {
            Box: require("jsx!../boxes/text"),
            PictureBox: require("jsx!../boxes/picture")
        }

    module.exports = React.createClass({
        getInitialState: function() {
            return {
                "box": null,
                "q": "",
                "temp": "",
            }
        },
        onSearch: function(event) {
            this.setState({"q": this.state.temp})
            event.preventDefault()
        },
        onEnable: function(event) {
            var target = $(event.target).closest("a")
            if (target.length) {
                if (this.state.box === target.data("id")) {
                    this.setState({"box": null})
                    this.props.onEnable(target.data("id"))
                } else {
                    this.setState({"box": target.data("id")})
                }
            } else {
                this.setState({"box": null})
            }
            return false
        },
        onSwap: function() {
            // do nothing
        },
        handleChange: function(event) {
            this.setState({"temp": event.target.value})
        },
        render: function() {
            var boxList,
                results,
                box,
                searchable = this.props.collection.search(this.state.q),
                found = false

            found = _.inject(searchable, _.bind(function(found, box) {
                return found || (box.get("id") == this.state.box)
            }, this), found)

            if (searchable.length) {
                var b

                //box = <p>&larr; Select a collection to preview it.</p>,
                results = <p>{searchable.length} matches for <em>{this.state.q}</em></p>
                box = <article className="box">
                        <header><h2>Preview</h2></header>
                    </article>

                if (this.state.box && found) {
                    b = this.props.collection.findWhere({id: this.state.box})
                } else {
                    b = searchable[0]
                }

                boxList = <BoxList boxes={searchable}
                                   current={b.get("id")}/>
                box = Boxes[b.get("box")](_.extend({onSwap: this.onSwap},
                                                   b.get("data")))

            } else if (this.state.q) {
                results = <p>No results match <em>{this.state.q}</em>.</p>
            }

            return (
                <div className={this.props.className} id={this.props.id}>
                    <div className="col-sm-8">
                        <h4>Find a collection</h4>
                    </div>
                    <form method="POST" action="/" onSubmit={this.onSearch}>
                    <div className="col-sm-4">
                        <div className="input-group">
                            <span className="input-group-addon">
                                <i className="glyphicon glyphicon-search"></i>
                            </span>
                            <input type="search" id="prototype-admin-search" name="q"
                                   className="form-control" placeholder="collection name"
                                   value={this.state.temp} onChange={this.handleChange} />
                        </div>
                    </div>
                    <div className="col-sm-4">
                        <p>
                            <button type="submit" className="btn btn-default">
                                Search
                            </button>
                        </p>
                    </div>
                    </form>
                    <div className="col-sm-8">
                        {results}
                    </div>
                    <div className="col-sm-4 clearfix" onClick={this.onEnable}>
                        {boxList}
                    </div>
                    <div className="col-sm-4">
                        {box}
                    </div>
                </div>
            )
        }
    })
})
