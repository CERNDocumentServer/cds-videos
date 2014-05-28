/** @jsx React.DOM **/
/*
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
//define(["backbone", "react"], function(Backbone, React) {
// CommonJS format
define(function(require, exports, module) {
    "use strict"

    var Backbone = require('backbone'),
        React = require('react')

    var Switch = React.createClass({
        render: function() {
            return (
                <p className="col-md-6">
                    <a href="#">{this.props.labels.on}</a>
                </p>
            )
        }
    })

    function Proto(foo) {
        this.foo = foo
        this.derp()
    }

    Proto.prototype = {
        constructor: Proto,
        derp: function() {
            alert(this.foo)
        }
    }

    // AMD format
    //return {
    //    Proto: Proto,
    //    Switch: Switch
    //};
    // CommonJS format
    exports.Proto = Proto
    exports.Switch = Switch
})
