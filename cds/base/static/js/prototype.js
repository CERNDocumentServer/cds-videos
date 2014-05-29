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

define(
    "prototype",
    ["jquery",
     "react",
     "jsx!prototype/boxes/text.js",
     "jsx!prototype/prototype.js",
     "jsx!prototype/row.js"],
    function($, React, text, proto, row)
{
    "use strict"

    var original = $("div.websearch")
        .before("<div id=prototype-topbar></div>")
        .before("<div id=prototype-row></div>")

    React.renderComponent(
        proto.TopBar({
            labels: {
                on: "Switch to all the collections",
                off: "Switch to your personal collections"
            },
            original: original,
            related: $("#prototype-row")
        }),
        $("#prototype-topbar")[0]
    )

    React.renderComponent(
        row.Row({
            boxes: [{
                    id: "b0",
                    box: text.Box({
                        title: "Title 1",
                        subtitle: "Subtitle 1",
                        body: "kikoo lol"
                    })
            }, {
                    id: "b1",
                    box: text.Box({
                        title: "Title 2",
                        subtitle: "Subtitle 2",
                        body: "kikoo lol"
                    })
            }, {
                    id: "b2",
                    box: text.Box({
                        title: "Title 3",
                        subtitle: "Subtitle 4",
                        body: "kikoo lol"
                    })
            }]
        }),
        $("#prototype-row")[0]
    )

    new proto.Proto("Hello world!")
})

require(["prototype"], function(prototype) {})
