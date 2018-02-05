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

"""CDS Admin views."""

from flask_admin.contrib.sqla import ModelView

from .models import Announcement


class AnnouncementsModelView(ModelView):
    """Announcements admin view."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    page_size = 20
    column_exclude_list = ['created', 'updated']
    column_searchable_list = ['message', 'path']
    column_default_sort = ('active', True)

    form_columns = ('message', 'path', 'style', 'start_date', 'end_date',
                    'active')

    form_choices = column_choices = {
        'style': [
            ('default', 'Gray'),
            ('success', 'Green '),
            ('info', 'Light blue'),
            ('warning', 'Yellow'),
            ('danger', 'Red')
        ]
    }

    column_descriptions = {
        'style': 'Color of the announcement\'s background.',
        'path': 'Enter the url path (including the first /) to define in '
                'which part of the site the message will be visible. For '
                'example, if you enter `/deposit`, any url starting with '
                '`/deposit` will show the announcement (/deposit, '
                '/deposit/upload, etc...). Leave it empty for any url.',
        'start_date': 'Set to current or future date/time to delay the '
                      'announcement.',
        'end_date': 'Leave empty value if you want it visible until you '
                    'manually disable it.'
    }

    def after_model_change(self, form, model, is_created):
        """Clean up old announcements after an action."""
        Announcement.disable_expired()

    def after_model_delete(self, model):
        """Clean up old announcements after an action."""
        Announcement.disable_expired()


announcements_adminview = dict(
    modelview=AnnouncementsModelView,
    model=Announcement,
    name='Announcements',
    category='CDS Announcements'
)
