# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2016, 2017, 2020 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CDS tests for Webhook receivers."""

from __future__ import absolute_import, print_function

import json

import mock
import pytest
from celery import states
from flask import url_for
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_records.models import RecordMetadata

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.flows.api import get_tasks_status_grouped_by_task_name
from cds.modules.flows.models import FlowMetadata
from helpers import (get_indexed_records_from_mock, get_object_count,
                     get_presets_applied, get_tag_count, mock_current_user,)


from invenio_files_rest.models import Bucket, ObjectVersion, ObjectVersionTag


# TODO: CHECK
@pytest.mark.skip(reason='TO BE CHECKED')
@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_receiver_local_file_pass(
        api_app, api_project, access_token, json_headers,
        db, local_file):
    """Test AVCWorkflow receiver."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    video_1_id = str(video_1.id)
    project_id = str(project.id)

    bucket_id = ObjectVersion.query.filter_by(
        version_id=local_file).one().bucket_id
    video_size = 5510872
    master_key = 'test.mp4'
    slave_keys = ['{0}.mp4'.format(quality)
                  for quality in get_presets_applied().keys()
                  if quality != '1024p']
    with api_app.test_request_context():
        url = url_for(
            'cds_flows.flow_list',
            access_token=access_token
        )

    with api_app.test_client() as client, \
            mock.patch('invenio_indexer.tasks.index_record.delay') \
            as mock_indexer:
        payload = dict(
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
            version_id=str(local_file),
            bucket_id=str(bucket_id),
        )
        # [[ RUN WORKFLOW ]]
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 200
        data = json.loads(resp.data.decode('utf-8'))
        assert '_tasks' in data
        assert data['key'] == master_key
        assert 'version_id' in data
        assert data.get('presets') == api_app.config[
            'CDS_OPENCAST_QUALITIES'].keys()
        assert 'links' in data  # TODO decide with links are needed

        assert ObjectVersion.query.count() == get_object_count()

        # Master file
        master = ObjectVersion.get(bucket_id, master_key)
        tags = master.get_tags()
        assert tags['_flow_id'] == data['tags']['_flow_id']
        assert master.key == master_key
        assert str(master.version_id) == data['version_id']
        assert master.file
        assert master.file.size == video_size

        # Check metadata tags
        metadata_keys = ['duration', 'bit_rate', 'size', 'avg_frame_rate',
                         'codec_name', 'codec_long_name', 'width', 'height',
                         'nb_frames', 'display_aspect_ratio', 'color_range']
        assert all([key in tags for key in metadata_keys])
        assert ObjectVersion.query.count() == get_object_count()
        assert ObjectVersionTag.query.count() == get_tag_count(is_local=True)

        # Check metadata patch
        recid = PersistentIdentifier.get('depid', video_1_depid).object_uuid
        record = Record.get_record(recid)
        assert 'extracted_metadata' in record['_cds']
        assert all([key in str(record['_cds']['extracted_metadata'])
                    for key in metadata_keys])

        # Check slaves
        for slave_key in slave_keys:
            slave = ObjectVersion.get(bucket_id, slave_key)
            tags = slave.get_tags()
            assert slave.key == slave_key
            assert '_sorenson_job_id' in tags
            assert tags['_sorenson_job_id'] == '1234'
            assert 'master' in tags
            assert tags['master'] == str(master.version_id)
            assert master.file
            assert master.file.size == video_size

        video = deposit_video_resolver(video_1_depid)
        # TODO: CHECK
        flows = FlowMetadata.get_by_deposit(video['_deposit']['id'])

        # check deposit tasks status
        tasks_status = get_tasks_status_grouped_by_task_name(flows)
        assert len(tasks_status) == 3
        assert 'file_transcode' in tasks_status
        assert 'file_video_extract_frames' in tasks_status
        assert 'file_video_metadata_extraction' in tasks_status

        # check tags (exclude 'uri-origin')
        assert ObjectVersionTag.query.count() == (get_tag_count() - 1)

        deposit = deposit_video_resolver(video_1_depid)

        # check ElasticSearch is called
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert video_1_id in ids
        assert project_id in ids
        assert deposit['_cds']['state'] == {
            'file_video_metadata_extraction': states.SUCCESS,
            'file_video_extract_frames': states.SUCCESS,
            'file_transcode': states.SUCCESS,
        }

    # Test cleaning!
    url = '{0}?access_token={1}'.format(data['links']['cancel'], access_token)

    with mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:
        # [[ DELETE WORKFLOW ]]
        resp = client.delete(url, headers=json_headers)

        assert resp.status_code == 200

        # check that object versions and tags are deleted
        # (Create + Delete) * Num Objs - 1 (because the file is local and will
        # be not touched)
        # calculated based on emptying ObjectVersion when deleting
        # so we get two ObjectVersion per file
        # TODO name the value of 2 and -1
        assert ObjectVersion.query.count() == 2 * get_object_count() - 1
        # Tags associated with the old version
        assert ObjectVersionTag.query.count() == get_tag_count(is_local=True)
        bucket = Bucket.query.first()
        # and bucket is empty
        assert bucket.size == 0

        record = RecordMetadata.query.filter_by(id=video_1_id).one()

        # check metadata patch are deleted
        assert 'extracted_metadata' not in record.json['_cds']
        # check the corresponding Event persisted after cleaning
        # TODO: CHECK
        assert len(FlowMetadata.get_by_deposit(record.json['_deposit']['id'])) == 0
        assert len(FlowMetadata.get_by_deposit(record.json['_deposit']['id'],
                                               _deleted=True)) == 1

        # check no reindexing is fired
        assert mock_indexer.called is False
