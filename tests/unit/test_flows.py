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
from cds_sorenson.api import get_all_distinct_qualities
from celery import states
from flask import url_for
from flask_principal import UserNeed, identity_loaded
from flask_security import current_user
from invenio_accounts.models import User
from invenio_accounts.testutils import login_user_via_session
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from invenio_records.models import RecordMetadata

from cds.modules.deposit.api import (deposit_project_resolver,
                                     deposit_video_resolver)
from cds.modules.flows.api import Flow
from cds.modules.flows.status import (get_deposit_flows,
                                      get_tasks_status_by_task)
from cds.modules.flows.models import Flow as FlowModel
from helpers import (get_indexed_records_from_mock, get_object_count,
                     get_presets_applied, get_tag_count, mock_current_user,
                     MockSorenson, MockSorensonHappy, MockSorensonFailed,
                     TestFlow, MOCK_TASK_NAMES, mock_compute_status,
                     mock_build_flow_status_json
                     )


from invenio_files_rest.models import Bucket, ObjectVersion, ObjectVersionTag


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_pass(api_app, db, api_project, access_token,
                           json_headers, mock_sorenson, online_video,
                           users):
    """Test AVCWorkflow."""
    project, video_1, video_2 = api_project
    video_1_depid = video_1['_deposit']['id']
    video_1_id = str(video_1.id)
    project_id = str(project.id)

    bucket_id = video_1['_buckets']['deposit']
    video_size = 5510872
    master_key = 'test.mp4'
    slave_keys = ['{0}.mp4'.format(quality)
                  for quality in get_presets_applied()
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
            uri=online_video,
            deposit_id=video_1_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 200
        data = json.loads(resp.data.decode('utf-8'))

        assert '_tasks' in data
        assert data['tags']['uri_origin'] == online_video
        assert data['key'] == master_key
        assert 'version_id' in data
        assert data.get('presets') == get_all_distinct_qualities()
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
        flows = get_deposit_flows(video['_deposit']['id'])

        # check deposit tasks status
        tasks_status = get_tasks_status_by_task(flows)
        assert len(tasks_status) == 4
        assert 'file_download' in tasks_status
        assert 'file_transcode' in tasks_status
        assert 'file_video_extract_frames' in tasks_status
        assert 'file_video_metadata_extraction' in tasks_status

        # check tags
        assert ObjectVersionTag.query.count() == get_tag_count()

        deposit = deposit_video_resolver(video_1_depid)

        # check ElasticSearch is called
        ids = set(get_indexed_records_from_mock(mock_indexer))
        assert video_1_id in ids
        assert project_id in ids
        assert deposit['_cds']['state'] == {
            'file_download': states.SUCCESS,
            'file_video_metadata_extraction': states.SUCCESS,
            'file_video_extract_frames': states.SUCCESS,
            'file_transcode': states.SUCCESS,
        }

    # check feedback from anoymous user
    flow_id = data['tags']['_flow_id']
    with api_app.test_request_context():
        url = url_for('cds_flows.flow_feedback_item',
                      flow_id=flow_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 401
    # check feedback from owner
    with api_app.test_request_context():
        url = url_for('cds_flows.flow_feedback_item',
                      flow_id=flow_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[0]).email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 200
    # check feedback from another user without access
    with api_app.test_request_context():
        url = url_for('cds_flows.flow_feedback_item',
                      flow_id=flow_id,
                      receiver_id='avc')
    with api_app.test_client() as client:
        login_user_via_session(client, email=User.query.get(users[1]).email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 403
    # check feedback from another user with access
    user_2 = User.query.get(users[1])
    user_2_id = str(user_2.id)
    user_2_email = user_2.email
    project = deposit_project_resolver(project['_deposit']['id'])
    project['_access'] = {'update': [user_2_email]}
    project = project.commit()
    with api_app.test_request_context():
        url = url_for('cds_flows.flow_feedback_item',
                      flow_id=flow_id,
                      )
    with api_app.test_client() as client:

        @identity_loaded.connect
        def load_email(sender, identity):
            if current_user.get_id() == user_2_id:
                identity.provides.update([UserNeed(user_2_email)])

        login_user_via_session(client, email=user_2_email)
        resp = client.get(url, headers=json_headers)
        assert resp.status_code == 200

    # Test cleaning!
    url = '{0}?access_token={1}'.format(data['links']['cancel'], access_token)

    with mock.patch('invenio_indexer.tasks.index_record.delay') as mock_indexer, \
            api_app.test_client() as client:
        resp = client.delete(url, headers=json_headers)
        assert resp.status_code == 200

        # check that object versions and tags are deleted
        # (Create + Delete) * Num Objs
        assert ObjectVersion.query.count() == 2 * get_object_count() - 1
        # Tags connected with the old version
        assert ObjectVersionTag.query.count() == get_tag_count()
        bucket = Bucket.query.first()
        # and bucket is empty
        assert bucket.size == 0

        record = RecordMetadata.query.filter_by(id=video_1_id).one()

        # check metadata patch are deleted
        assert 'extracted_metadata' not in record.json['_cds']

        # check the corresponding flow persisted after cleaning
        assert len(get_deposit_flows(record.json['_deposit']['id'])) == 0
        assert len(get_deposit_flows(record.json['_deposit']['id'],
                                     _deleted=True)) == 1

        # check no reindexing is fired
        assert mock_indexer.called is False


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_clean_download(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'

    with api_app.test_request_context():
        url = url_for(
            'cds_flows.flow_list',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 200

    assert ObjectVersionTag.query.count() == get_tag_count()
    flow = FlowModel.query.first()
    flow = Flow(model=flow)
    # [[ CLEAN DOWNLOAD ]]
    flow.clean_task(task_name='file_download')

    # check extracted metadata is there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_cds']

    # Create + Clean 1 Download File
    assert ObjectVersion.query.count() == get_object_count() + 1
    assert ObjectVersionTag.query.count() == get_tag_count()

    # RUN again
    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 200

    # Create + Clean 1 Download File + Run First Step
    assert ObjectVersion.query.count() == (get_object_count() * 2) + 1
    assert ObjectVersionTag.query.count() == get_tag_count() * 2


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_clean_video_frames(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'cds_flows.flow_list',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))

        assert resp.status_code == 200

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    flow = FlowModel.query.first()

    # [[ CLEAN VIDEO EXTRACT FRAMES ]]
    flow = Flow(model=flow)
    flow.clean_task(task_name='file_video_extract_frames')

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' in records[0].json['_cds']

    # Create + Clean Frames
    assert ObjectVersion.query.count() == (
        get_object_count() + get_object_count(download=False, transcode=False)
    )
    assert ObjectVersionTag.query.count() == get_tag_count()


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_clean_video_transcode(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'cds_flows.flow_list',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 200

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()

    #
    # CLEAN
    #
    presets = [p for p in get_presets_applied() if p != '1024p']
    for i, preset_quality in enumerate(presets, 1):
        # Clean transcode task for each preset

        flow = Flow(model=FlowModel.query.first())
        flow.clean_task(flow=flow, task_name='file_transcode',
                        preset_quality=preset_quality)

        # check extracted metadata is there
        records = RecordMetadata.query.all()
        assert len(records) == 1
        assert 'extracted_metadata' in records[0].json['_cds']

        # Create + Delete i-th transcoded files
        assert ObjectVersion.query.count() == get_object_count() + i
        assert ObjectVersionTag.query.count() == get_tag_count()

    # Create + Delete transcoded files
    assert ObjectVersion.query.count() == get_object_count() + len(presets)
    assert ObjectVersionTag.query.count() == get_tag_count()


@mock.patch('flask_login.current_user', mock_current_user)
def test_avc_workflow_clean_extract_metadata(
        api_app, db, cds_depid, access_token, json_headers,
        mock_sorenson, online_video):
    """Test AVCWorkflow receiver."""
    master_key = 'test.mp4'
    with api_app.test_request_context():
        url = url_for(
            'cds_flows.flow_list',
            access_token=access_token
        )

    with api_app.test_client() as client:
        payload = dict(
            uri=online_video,
            deposit_id=cds_depid,
            key=master_key,
            sleep_time=0,
        )
        # [[ RUN ]]
        resp = client.post(url, headers=json_headers, data=json.dumps(payload))
        assert resp.status_code == 200

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()
    # [[ CLEAN VIDEO METADATA EXTRACTION ]]
    flow = FlowModel.query.first()
    flow = Flow(model=flow)
    flow.clean_task(task_name='file_video_metadata_extraction')

    # check extracted metadata is not there
    records = RecordMetadata.query.all()
    assert len(records) == 1
    assert 'extracted_metadata' not in records[0].json['_cds']

    assert ObjectVersion.query.count() == get_object_count()
    assert ObjectVersionTag.query.count() == get_tag_count()
