{#
## This file is part of CDS.
## Copyright (C) 2015 CERN.
##
## CDS is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#}

{%- extends "format/record/multimedia/layout.tpl" -%}
{% import 'records/helpers/multimedia.html' as _multimedia  with context %}
{% import 'records/helpers/record.html' as _record with context %}
{%- block body -%}
    <div class"row">
        <div class="col-md-3">
            <dl>
                <dt><h4><i class="glyphicon glyphicon-camera"></i> Photographer</h4></dt>
                <dd>{{ _record.author(with_link=True) }}</dd>
            </dl>
            <dl>
                <dt><h4><i class="glyphicon glyphicon-calendar"></i> Date</h4></dt>
                <dd>{{ _record.date() }}</dd>
            </dl>
            <dl>
                <dt><h4><i class="glyphicon glyphicon-file"></i> Access</h4></dt>
                <dd>{{ record.get('medium.material') }}</dd>
            </dl>
            <dl>
                <dt><h4><i class="glyphicon glyphicon-tags"></i> &nbsp;Keywords</h4></dt>
                <dd>{{ _record.keywords(with_link=True) }}</dd>
            </dl>
            <hr />
            <p>{{ _record.copyright() | safe}}</p>
        </div>
        <div class="col-md-9">
            <div class="row">
                {{ _multimedia.thumbnails() }}
            </div>
        </div>
    </div>
{%- endblock -%}
