# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017, 2018 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Helper methods for CDS records."""

from __future__ import absolute_import, print_function

from flask import current_app, g, request
from six.moves.html_parser import HTMLParser
from six.moves.urllib.parse import urlparse

from invenio_search import current_search
from invenio_search.utils import schema_to_index


def schema_prefix(schema):
    """Get index prefix for a given schema."""
    if not schema:
        return None
    index, doctype = schema_to_index(
        schema, index_names=current_search.mappings.keys())
    return index.split('-')[0]


def is_record(record):
    """Determine if a record is a bibliographic record."""
    return schema_prefix(record.get('$schema')) == 'records'


def is_deposit(record):
    """Determine if a record is a deposit record."""
    return schema_prefix(record.get('$schema')) == 'deposits'


def get_user_provides():
    """Extract the user's provides from g."""
    provides = []
    for need in g.identity.provides:
        try:
            provides.append(need.value.lower())
        except AttributeError:
            # Add the user ID (integer) to the list
            provides.append(need.value)
    return provides


def remove_html_tags(html_tag_remover, value):
    """Remove any HTML tags."""
    html_tag_remover.reset()
    html_tag_remover.feed(value)
    return html_tag_remover.get_data()


def format_pid_link(url_template, pid_value):
    """Format a pid url."""
    if request:
        return url_template.format(
            host=request.host,
            scheme=request.scheme,
            pid_value=pid_value,
        )
    else:
        r = urlparse(current_app.config['THEME_SITEURL'])
        return url_template.format(
            host=r.netloc,
            scheme=r.scheme,
            pid_value=pid_value,
        )


class HTMLTagRemover(HTMLParser):
    """Remove all HTML tags by keeping only the value within the tag."""
    values = []

    def reset(self):
        """Reset the list of values."""
        HTMLParser.reset(self)
        self.values = []

    def handle_data(self, data):
        """Append only the value within the tags."""
        self.values.append(data)

    def get_data(self):
        """Return only values."""
        return ''.join(self.values)
