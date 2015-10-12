# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""CDS Photo record spliter"""

import urlparse

from functools import partial

from .default import _force_list, _reverse_force_list, RecordSplitter

from .errors import Double037FieldException, UnknownHostnameWarning


class PhotoSplitter(RecordSplitter):
    """CDS photo splitter"""

    _main_record_type = 'ALBUM'

    _new_record_type = 'IMAGE'

    _copy_fields_list = [
        # authors
        u'100__',
        u'700__',
        # titles
        u'245__',
        u'246__',
        # date, location, imprint
        u'260__',
        u'269__',
        # copyrgiht and licence
        u'540__',
        u'542__',
    ]

    # to make sure all existing hostnames are taken into account,
    # we define both banned and allowed
    _q_banned_hostnames = [
        'http://preprints.cern.ch',
        'http://documents.cern.ch']

    q_allowed_hostnames = [
        'http://doc.cern.ch',
        'http://cds.cern.ch',
        'http://cdsweb.cern.ch',
        'https://cds.cern.ch']

    @classmethod
    def banned_hostname(cls, url):
        """Check if the url's hostname is banned"""

        check = partial(lambda hostname, url: url.startswith(hostname),
                        url=url)
        return any(map(check, cls._q_banned_hostnames))

    @classmethod
    def allowed_hostname(cls, url):
        """Check if the url's hostname is banned"""

        check = partial(lambda hostname, url: url.startswith(hostname),
                        url=url)
        return any(map(check, cls._q_allowed_hostnames))

    @classmethod
    def predicate(cls, field):
        """Should the file be kept?"""

        return (
            (
                not field.get('x') or
                not field.get('x').startswith('icon')
            ) and (
                field.get('u') or (
                    field.get('q') and
                    cls.allowed_hostname(field.get('q'))
                )
            )
        )

    def filter_8564_(self, record):
        """Create filter for 8564_ tags"""

        def unique_key(media_field):
            return media_field.get('8')

        return RecordSplitter.common_filter(record, u'8564_',
                                            self.predicate, unique_key)

    def filter_8567_(self, record):
        """Create filter for 8567_ tags"""

        def unique_key(media_field):
            return media_field.get('8')

        def predicate(media_field):
            return media_field.get('2') == 'MediaArchive'

        return self.common_filter(record, u'8567_', predicate, unique_key)

    def remove_8564_(self, record):
        """Create remover for 8564_ tags"""

        field_tag = u'8564_'
        data = _force_list(record[field_tag])

        # make sure that all the hostnames are known
        def is_known_hostname(url):
            return self.allowed_hostname(url) or self.banned_hostname(url)

        q_list = map(is_known_hostname,
                     [elm.get('q') for elm in data if elm.get('q')])
        if not all(q_list):
            raise UnknownHostnameWarning

        cleared_field = []

        for field in _force_list(data):
            if field.get('x', '').startswith('icon'):
                continue
            # remove all fields without url
            has_url = False
            for key, value in field.iteritems():
                url_pieces = urlparse.urlparse(value)
                if url_pieces.scheme and url_pieces.netloc:
                    has_url = True
                    break
            if not has_url:
                continue

            if not self.predicate(field):
                record_url = field.get('q')
                if not record_url or not (
                        self.allowed_hostname(record_url) or
                        self.banned_hostname(record_url)
                ):
                    cleared_field.append(field)

        return self.common_remove(record, field_tag, cleared_field)

    def remove_8567_(self, record):
        """Remover for 8567_ marc tag"""

        field_tag = u'8567_'
        data = _force_list(record[field_tag])

        cleared_field = [field for field in data if
                         field.get('2') != 'MediaArchive']

        return self.common_remove(record, field_tag, cleared_field)

    def copy_037__(self, main_record, new_record):
        """Copier for 037 (report number)"""

        if not isinstance(main_record[u'037__'], dict):
            raise Double037FieldException

        common_field = main_record[u'037__']['a']
        if new_record.get(u'8564_'):
            counter = new_record.get(u'8564_')[0].get('8', '01')
        elif new_record.get(u'8567_'):
            counter = new_record.get(u'8567_')[0].get('8', '01')

        new_record[u'037__'] = {
            'a': '-'.join([common_field, counter])
        }

    def _transform_record(self, record):
        """Split photo records"""

        record, new_records = super(PhotoSplitter,
                                    self)._transform_record(record)
        for rec in new_records:
            for tag in [u'8564_', u'8567_']:
                if rec.get(tag):
                    rec[tag] = _reverse_force_list(rec[tag])

        return record, new_records
