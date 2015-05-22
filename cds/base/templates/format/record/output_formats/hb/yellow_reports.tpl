{#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#}
{%- import 'helpers/format/record/general/yellow_reports_macros.html' as _helpers -%}
<div class="media">
    <div class="media-left media-middle">
        <a href="{{ url_for('record.metadata', recid=record._id) }}">
            <img class="media-object" width="80" height="100" src="{{_helpers.yellow_reports_cover(record.url, 'icon-180') }}"/>
        </a>
    </div>
    <div class="media-body">
        <h4 class="media-heading"><a href="{{ url_for('record.metadata', recid=record._id) }}">{{ _helpers.yellow_reports_title(record.meeting_names) }}</a></h4>
            <ul class="list-inline">
                <li>ISBN: {{ record.isbn.isbn }} ({{record.isbn.medium}})</li>
                <li>DOI: {{ record.doi }}</li>
                <li>{{ _('Authors') }}
                {% for author in record.authors %}
                {{author.full_name}} ({{ author.affiliation }})
                {% endfor %}
                </li>
            </ul>
    </div>
</div>
