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
    "main",
    ["jquery",
     "react",
     "jsx!prototype/prototype.js"],
    function($, React, proto, _data)
{
    "use strict"

    var boxes = [
        {box: "Box", data: {
            title: "Polarisation confirmed",
            href: "http://cds.cern.ch/record/1698254?ln=en",
            subtitle: "by Anaïs Schaeffer, the CERN Bulletin",
            body: '<img src="https://cds.cern.ch/record/1698254/files/LHCbEvent_1_image.jpg?subformat=icon" alt="" style="margin:0 1em 1em 0;width:50%" align="left">' +
                  '<p>The polarisation of photons emitted in the decay of a bottom quark into a strange quark, as predicted by the Standard Model, has just been observed for the first time by the LHCb collaboration. More detailed research is still required to determine the value of this polarisation with precision.</p>',
            footer: "visit the CERN Bulletin",
            more: "http://cds.cern.ch/journal/CERNBulletin/2014/20/News%20Articles"
        }},
        {box: "Box", data: {
            title: "Helix Nebula",
            href: "http://cds.cern.ch/collection/Helix%20Nebula",
            subtitle: "The Science Cloud",
            body: '<ul>' +
                  '<li><a href="#">D7.4: Information as a Service – Towards Value Co-Creation in …</a></li>' +
                  '<li><a href="#">D7.3:Costing exercise comparing in-house vs. cloud based operation …</a></li>' +
                  '<li><a href="#">MS19_Governance Model Workshop 2</a></li>' +
                  '<li><a href="#">MS12_Security Challenge Performed </a></li>' +
                  '<li><a href="#">MS16:Technical workshop (co-located with EGI Technical Forum 2013)</a></li>' +
                  '<li><a href="#">D7.2_Synthesis and Analysis of Overall Business Models</a></li>' +
                  '</ul>',
            footer: "more recent publications"
        }},
        {box: "Box", data: {
            title: "Recent book",
            href: "http://cds.cern.ch/collection/Books",
            body: '<img src="http://ecx.images-amazon.com/images/I/51YgkOd%2BBpL._SL160_.jpg" alt="" style="margin:0 1em 1em 0" align="left">' +
                  '<h3>Discrete of continuous? : the quest for fundamental length in modern physics</h3>' +
                  '<p>by Hagar, Amit</p>',
            footer: "more recent books"
        }},
        {box: "Box", data: {
            title: "AIDA",
            href: "http://cds.cern.ch/collection/AIDA",
            img: 'http://cds.cern.ch/img/AIDA_logo_mini.png',
            body: '<h3>Latest additions</h3>' +
                  '<ul>' +
                  '<li><a href="#">2nd Periodic Report Public version</a></li>' +
                  '<li><a href="#">Recent results of the ATLAS Upgrade Planar Pixel Sensors R&amp;D Project</a></li>' +
                  '<li><a href="#">RADIATION MONITORING AT GIF++</a></li>' +
                  '</ul>',
            footer: "more from AIDA"
        }},
        {box: "Box", data: {
            title: "Your tags",
            href: "/youraccount/yourtags/",
            body:
                '<p>' +
                    '<a href="/youraccounts/tags/architecture/" style="font-size: 20px;">architecture</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/art/" style="font-size: 28px;">art</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/autumn/" style="font-size: 14px;">autumn</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/band/" style="font-size: 14px;">band</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/barcelona/" style="font-size: 12px;">barcelona</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/beach/" style="font-size: 27px;">beach</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/berlin/" style="font-size: 14px;">berlin</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/bike/" style="font-size: 12px;">bike</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/california/" style="font-size: 27px;">california</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/green/" style="font-size: 20px;">green</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/halloween/" style="font-size: 12px;">halloween</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/hawaii/" style="font-size: 13px;">hawaii</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/holiday/" style="font-size: 18px;">holiday</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/house/" style="font-size: 15px;">house</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/nature/" style="font-size: 29px;">nature</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/nyc/" style="font-size: 23px;">nyc</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/ocean/" style="font-size: 14px;">ocean</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/river/" style="font-size: 16px;">river</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/rock/" style="font-size: 18px;">rock</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/sky/" style="font-size: 23px;">sky</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/snow/" style="font-size: 23px;">snow</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/spain/" style="font-size: 19px;">spain</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/spring/" style="font-size: 18px;">spring</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/summer/" style="font-size: 25px;">summer</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/sun/" style="font-size: 15px;">sun</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/sunset/" style="font-size: 22px;">sunset</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/taiwan/" style="font-size: 20px;">taiwan</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/texas/" style="font-size: 17px;">texas</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/trip/" style="font-size: 22px;">trip</a>&nbsp; ' +
                    '<a href="/youraccounts/tags/washington/" style="font-size: 15px;">washington</a>&nbsp; ' +
                '</p>',
            footer: "all your 300 tags"
        }},
        {box: "PictureBox", data: {
            title: "Photos",
            img: "http://cds.cern.ch/record/1700467/files/_B1A0931.jpg?subformat=icon-640",
            href: "http://cds.cern.ch/collection/Photos",
            body: '<p><a href="#">CERN openlab Automation and Controls Competence Center - Team 2013</a></p>',
            footer: "more photos"
        }}
    ];

    var rows = [[]],
        grid = {rows: [], personal: true}
    $.each(boxes, function(i, box) {
        if (!rows[rows.length - 1] || rows[rows.length - 1].length >= 3) {
            rows.push([])
        }
        rows[rows.length - 1].push({
            id: "b" + i,
            box: proto[box.box](box.data)
        })
    })
    $.each(rows, function(i, row) {
        grid.rows.push({
            id: "r" + i,
            row: proto.Row({boxes: row})
        })
    })

    var original = $("div.websearch")
        .before("<div id=prototype-topbar></div>")
        .before("<div id=prototype-adminbar></div>")
        .before("<div id=prototype-row></div>")

    var topBar = React.renderComponent(proto.TopBar({
                labels: {
                    on: "Switch to all the collections",
                    off: "Switch to your personal collections"
                },
                personal: "true",
                eventsName: {
                    "switch": "prototype:switch",
                    "admin": "prototype:admin"
                },
            }), $("#prototype-topbar")[0]),
        adminBar = React.renderComponent(
            proto.AdminBar({
                admin: false
            }), $("#prototype-adminbar")[0]),
        grid = React.renderComponent(proto.Grid(grid), $("#prototype-row")[0])

    $(document)
    .on("prototype:switch", function(event, show) {
        var props = {personal: show}
        adminBar.setProps(props)
        topBar.setProps(props)
        grid.setProps(props)

        if (show) {
            original.hide()
        } else {
            original.show()
        }
    })
    .on("prototype:admin", function(event, show) {
        var props = {admin: show}
        topBar.setProps(props)
        adminBar.setProps(props)
    })
    .trigger("prototype:switch", [true])
    .trigger("prototype:admin", [false])
})

require(["main"], function(main) {})
