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
"""Record API."""

from __future__ import absolute_import, print_function

import os
import uuid
from os.path import splitext

from flask import current_app
from invenio_files_rest.models import ObjectVersion, ObjectVersionTag
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.api import FileObject, FilesIterator, Record
from invenio_records_files.utils import sorted_files_from_bucket
from sqlalchemy import func

from .fetchers import recid_fetcher
from .minters import kwid_minter


def dump_object(obj):
    """Dump a object."""
    tags = obj.get_tags()
    # File information
    content_type = splitext(obj.key)[1][1:].lower()
    context_type = tags.pop('context_type', '')
    media_type = tags.pop('media_type', '')
    return {
        'key': obj.key,
        'bucket_id': str(obj.bucket_id),
        'version_id': str(obj.version_id),
        'checksum': obj.file.checksum if obj.file else '',
        'size': obj.file.size if obj.file else 0,
        'file_id': str(obj.file_id),
        'completed': obj.file is not None,
        'content_type': content_type,
        'context_type': context_type,
        'media_type': media_type,
        'tags': tags,
        'links': _build_file_links(obj)
    }


def _build_file_links(obj):
    """Return a dict with file links."""
    return dict(
        self=(
            u'{scheme}://{host}/{api}/{bucket}/{key}?versionId={version_id}'
            .format(
                # TODO: JSONSchema host is not the best solution here.
                scheme=current_app.config['JSONSCHEMAS_URL_SCHEME'],
                host=current_app.config['JSONSCHEMAS_HOST'],
                api=current_app.config['DEPOSIT_FILES_API'].strip('/'),
                bucket=obj.bucket_id,
                key=obj.key,
                version_id=obj.version_id,
            )))


def dump_generic_object(obj, data):
    """Dump a generic object (master, subtitles, ..) avoid depending objs."""
    obj_dump = dump_object(obj)
    # if it's a master, get all the depending object and add them inside
    # <context_type> as a list order by key.
    for slave in ObjectVersion.get_by_bucket(bucket=obj.bucket).join(
            ObjectVersion.tags).filter(
                ObjectVersionTag.key == 'master',
                ObjectVersionTag.value == str(obj.version_id)).order_by(
                    func.length(ObjectVersion.key), ObjectVersion.key):
        obj_dump.setdefault(slave.get_tags()['context_type'], []).append(
            dump_object(slave))
    # Sort slaves by key within their lists
    data.update(obj_dump)


class CDSFileObject(FileObject):
    """Wrapper for files."""

    @classmethod
    def _link(cls, bucket_id, key, _external=True):
        return u'{scheme}://{host}/{api}/{bucket_id}/{key}'.format(
            scheme=current_app.config['JSONSCHEMAS_URL_SCHEME'],
            host=current_app.config['JSONSCHEMAS_HOST'],
            api=current_app.config['DEPOSIT_FILES_API'].lstrip('/'),
            bucket_id=bucket_id,
            key=key,
        )

    def dumps(self):
        """Create a dump of the metadata associated to the record."""
        dump_generic_object(obj=self.obj, data=self.data)
        return self.data


class CDSFilesIterator(FilesIterator):
    """Iterator for files."""

    def dumps(self, bucket=None):
        """Serialize files from a bucket."""
        files = []
        for o in sorted_files_from_bucket(bucket or self.bucket, self.keys):
            if 'master' in o.get_tags():
                continue
            dump = self.file_cls(o, self.filesmap.get(o.key, {})).dumps()
            if dump:
                files.append(dump)
        return files


class CDSVideosFilesIterator(CDSFilesIterator):
    """Video files iterator."""

    @staticmethod
    def get_master_video_file(record):
        """Get master video file from a Video record."""
        try:
            return next(f for f in record['_files']
                        if f['media_type'] == 'video'
                        and f['context_type'] == 'master')
        except StopIteration:
            return {}

    @staticmethod
    def get_video_subformats(master_file):
        """Get list of video subformats."""
        return [
            video for video in master_file.get('subformat', [])
            if video['media_type'] == 'video'
            and video['context_type'] == 'subformat'
        ]

    @staticmethod
    def get_video_subtitles(record):
        """Get list of video subtitles."""
        return [
            f for f in record['_files']
            if f['context_type'] == 'subtitle' and 'language' in f['tags']
        ]

    @staticmethod
    def get_video_frames(master_file):
        """Get sorted list of video frames."""
        return sorted(
            master_file.get('frame', []),
            key=lambda s: float(s['tags']['timestamp']))

    @staticmethod
    def get_video_posterframe(record):
        """Get the video poster frame."""
        # First check if we have a custom thumbnail for this video
        for f in record.get('_files'):
            if f.get('context_type') == 'poster' and f.get(
                    'media_type') == 'image':
                return f

        # If not return the first frame from the list
        master_file = CDSVideosFilesIterator.get_master_video_file(record)
        return CDSVideosFilesIterator.get_video_frames(master_file)[0]


class CDSRecord(Record):
    """CDS Record."""

    file_cls = CDSFileObject

    files_iter_cls = CDSFilesIterator

    record_fetcher = staticmethod(recid_fetcher)

    @property
    def pid(self):
        """Return an instance of record PID."""
        pid = self.record_fetcher(self.id, self)
        return PersistentIdentifier.get(pid.pid_type, pid.pid_value)

    @property
    def depid(self):
        """Return depid of the record."""
        return PersistentIdentifier.get(
            pid_type='depid', pid_value=self.get('_deposit', {}).get('id'))


class Keyword(Record):
    """Define API for a keywords."""

    _schema = 'keywords/keyword-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a keyword."""
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)

        key_id = data.get('key_id', None)
        name = data.get('name', None)
        data.setdefault('deleted', False)

        if not id_:
            id_ = uuid.uuid4()
            kwid_minter(id_, data)

        data['suggest_name'] = {
            'input': name,
            'payload': {
                'key_id': key_id,
                'name': name
            },
        }
        return super(Keyword, cls).create(data=data, id_=id_, **kwargs)

    @property
    def ref(self):
        """Get the url."""
        return Keyword.get_ref(self['key_id'])

    @classmethod
    def get_id(cls, ref):
        """Get the ID from the reference."""
        return os.path.basename(ref)

    @classmethod
    def get_ref(cls, id_):
        """Get reference from an ID."""
        return 'https://cds.cern.ch/api/keywords/{0}'.format(str(id_))


class Category(Record):
    """Define API for a category."""

    _schema = 'categories/category-v1.0.0.json'

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a category."""
        data['$schema'] = current_jsonschemas.path_to_url(cls._schema)

        data['suggest_name'] = {
            'input': data.get('name', None),
            'payload': {
                'types': data.get('types', [])
            }
        }
        return super(Category, cls).create(data=data, id_=id_, **kwargs)
