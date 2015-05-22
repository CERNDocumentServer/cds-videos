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
<div class="collection-record-cover">
    <div class="row">
        <div class="col-md-1">
            <h4 class="media-heading"><span class="label label-primary">Latest report</span></h4>
        </div>
        <div class="col-md-3">
            <a href="{{ url_for('record.metadata', recid=record._id) }}">
                <img class="img-responsive" src="{{_helpers.yellow_reports_cover(record.url, 'icon-700') }}"/>
            </a>
        </div>
        <div class="col-md-8">
            <h2 class="media-heading"><a href="{{ url_for('record.metadata', recid=record._id) }}">{{ _helpers.yellow_reports_title(record.meeting_names) }}</a></h2>
            <p> {{record.abstract.summary}} </p>
            <ul>
                <li>ISBN: {{ record.isbn.isbn }} ({{record.isbn.medium}})</li>
                <li>DOI: {{ record.doi }}</li>
                <li>{{ _('Authors') }}
                {% for author in record.authors %}
                {{author.full_name}} ({{ author.affiliation }})
                {% endfor %}
                </li>
                <li>{{_('Subject')}}: {{ record.subject.term }}</li>
                <li>{{_('License')}}: {{ record.license.material }} {{record.license.license}}</li>
                <li>{{_('Notes')}}: {{ record.comment }}</li>
                <li>{{_('Imprint')}}: {{ record.imprint.place }}: {{ record.imprint.publisher_name }}, {{ record.imprint.date }} - {{ record.physical_description.pagination}}</li>
            </ul>
        </div>
    </div>
</div>
