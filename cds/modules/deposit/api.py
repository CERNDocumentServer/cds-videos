# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
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

"""Deposit API."""

from __future__ import absolute_import, print_function

import os

from flask import url_for
from invenio_deposit.api import Deposit
from invenio_files_rest.models import Bucket, Location, MultipartObject
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_files.models import RecordsBuckets

from .errors import DiscardConflict


class CDSDeposit(Deposit):
    """Define API for changing deposit state."""

    @classmethod
    def create(cls, data, id_=None):
        """Create a deposit.

        Adds bucket creation immediately on deposit creation.
        """
        bucket = Bucket.create(
            default_location=Location.get_default()
        )
        data['_buckets'] = {'deposit': str(bucket.id)}
        deposit = super(CDSDeposit, cls).create(data, id_=id_)
        RecordsBuckets.create(record=deposit.model, bucket=bucket)
        return deposit

    @property
    def multipart_files(self):
        """Get all multipart files."""
        return MultipartObject.query_by_bucket(self.files.bucket)


def video_resolver(ids):
    """Get records from PIDs."""
    pids = [p.object_uuid for p in PersistentIdentifier.query.filter(
        PersistentIdentifier.pid_value.in_(ids)).all()]
    return Video.get_records(pids)


def deposit_build_url(video_id):
    """Build video url."""
    return url_for('invenio_deposit_ui.depid', pid_value=video_id)


def record_build_url(video_id):
    """Build video url."""
    return url_for('invenio_records_ui.recid', pid_value=str(video_id))


def record_unbuild_url(url):
    """Extract the PID from the deposit/record url."""
    # TODO can we improve it?
    return os.path.basename(url)


def is_deposit(url):
    """Check if it's a deposit or a record."""
    # TODO can we improve check?
    return url.startswith('/deposit')


class Project(CDSDeposit):
    """Define API for a project."""

    @property
    def video_ids(self):
        """Get all video ids.

        .. note::

            If the video is published, it returns the recid.
            Otherwise, the ``video['_deposit']['id']``.

        :returns: A list of video ids.
        """
        return [record_unbuild_url(ref) for ref in self.video_refs]

    @property
    def video_refs(self):
        """Get all video refs.

        :returns: A list of video references.
        """
        return [video['$reference'] for video in self['videos']]

    def _find_refs(self, refs):
        """Find index of references."""
        result = {}
        for (key, value) in enumerate(self.video_refs):
            try:
                refs.index(value)
                result[key] = value
            except ValueError:
                pass
        return result

    def _update_videos(self, old_refs, new_refs):
        """Update metadata with new video references.

        :param old_refs: List contains the video references to substitute.
        :param new_refs: List contains the new video references
        """
        for (key, value) in enumerate(self.video_refs):
            try:
                index = old_refs.index(value)
                self['videos'][key] = {'$reference': new_refs[index]}
            except ValueError:
                pass

    def _delete_videos(self, refs):
        """Update metadata deleting videos.

        :param refs: List contains the video references to delete.
        """
        for index in self._find_refs(refs).keys():
            del self['videos'][index]

    def publish(self, pid=None, id_=None):
        """Publish a project.

        The publishing involve the publication of all the videos inside.

        :returns: The new project version.
        """
        # get reference of all deposit still not published
        refs_old = [video_ref for video_ref in self.video_refs
                    if is_deposit(video_ref)]
        # extract the PIDs from them
        ids_old = [record_unbuild_url(video_ref) for video_ref in refs_old]
        # publish them and get the new PID
        refs_new = [record_build_url(video.publish()['recid'])
                    for video in video_resolver(ids_old)]
        # update project video references
        self._update_videos(refs_old, refs_new)
        # publish project
        return super(Project, self).publish(pid=pid, id_=id_)

    def discard(self, pid=None):
        """Discard project changes."""
        _, record = self.fetch_published()
        # if the list of videos is different return error
        if self['videos'] != record['videos']:
            raise DiscardConflict()
        # discard project
        return super(Project, self).discard(pid=pid)

    def _add_video(self, video):
        """Add a video."""
        video_ref = video.ref
        indices = self._find_refs([video_ref])
        if indices:
            # update video refs
            self['videos'][indices[video_ref]] = {'$reference': video_ref}
        else:
            # add new one
            self['videos'].append({'$reference': video_ref})


class Video(CDSDeposit):
    """Define API for a video."""

    @property
    def ref(self):
        """Get video id."""
        if self.status == 'published':
            return record_build_url(self['recid'])
        else:
            return deposit_build_url(self['_deposit']['id'])

    @property
    def project(self):
        """Get the related project."""
        if not hasattr(self, '_project'):
            try:
                project_id = self['_deposit']['project_id']
            except KeyError:
                return None
            project_pid = PersistentIdentifier.query.filter_by(
                pid_value=project_id).one()
            self._project = Project.get_record(id_=project_pid.object_uuid)
        return self._project

    @project.setter
    def project(self, project):
        """Set a project."""
        self['_deposit']['project_id'] = project['_deposit']['id']
        project._add_video(self)

    def publish(self, pid=None, id_=None):
        """Publish a video and update the related project."""
        # save a copy of the old PID
        video_old_id = self['_deposit']['id']
        # publish the video
        super(Video, self).publish(pid=pid, id_=id_)
        (_, record_new) = self.fetch_published()
        # update associated project
        self.project._update_videos(
            [deposit_build_url(video_old_id)],
            [record_build_url(record_new['recid'])]
        )
        self.project.commit()
        return self

    def edit(self, pid=None):
        """Edit a video and update the related project."""
        # save a copy of the recid
        video_old_id = self['recid']
        # edit the video
        video_new = super(Video, self).edit(pid=pid)
        # update associated project
        self.project._update_videos(
            [record_build_url(video_old_id)],
            [deposit_build_url(video_new['_deposit']['id'])]
        )
        self.project.commit()
        return video_new
