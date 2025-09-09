# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2025 CERN.
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


"""Tests for external user permissions."""

import json
from io import BytesIO

from flask import url_for
from flask_principal import AnonymousIdentity, UserNeed, identity_loaded
from flask_security import current_user, login_user, logout_user
from helpers import prepare_videos_for_publish
from invenio_access import Permission
from invenio_access.models import ActionRoles
from invenio_accounts.models import Role, User

from cds.modules.deposit.api import deposit_video_resolver
from cds.modules.records.permissions import (
    has_upload_permission,
    record_permission_factory,
    upload_access_action,
)


def test_has_upload_permission_external_user(app, external_user):
    """Test that external user without cern-user role cannot upload."""
    with app.test_request_context():
        user = User.query.get(external_user)
        login_user(user)

        # Test has_upload_permission function directly
        permission = Permission(upload_access_action)
        assert not permission.can()

        # Test has_upload_permission helper function
        assert not has_upload_permission()


def test_has_upload_permission_cern_user(app, users):
    """Test that authenticated user with cern-user role can upload."""
    with app.test_request_context():
        user = User.query.get(users[0])
        login_user(user)

        # Test has_upload_permission function directly
        permission = Permission(upload_access_action)
        assert permission.can()

        # Test has_upload_permission helper function
        assert has_upload_permission()


def test_record_create_permission_external_user(app, external_user, deposit_metadata):
    """Test record create permission for external user without role."""
    with app.test_request_context():
        user = User.query.get(external_user)
        login_user(user)

        # Test creating a record permission
        factory = record_permission_factory(record=deposit_metadata, action="create")
        assert not factory.can()


def test_project_rest_api_external_user_can_create(
    api_app, external_user, deposit_metadata, json_partial_project_headers
):
    """Test project creation via REST API for external user without role."""
    with api_app.test_client() as client:
        user = User.query.get(external_user)
        login_user(user)

        # Try to create a project via REST API
        resp = client.post(
            url_for("invenio_deposit_rest.project_list"),
            data=json.dumps(deposit_metadata),
            headers=json_partial_project_headers,
        )
        # Should be forbidden (403) because user doesn't have upload permission
        assert resp.status_code == 403


def test_video_rest_api_external_user(
    api_app, external_user, video_deposit_metadata, json_partial_project_headers
):
    """Test video creation via REST API for external user without role."""
    with api_app.test_client() as client:
        user = User.query.get(external_user)
        login_user(user)

        # Try to create a video via REST API
        resp = client.post(
            url_for("invenio_deposit_rest.video_list"),
            data=json.dumps(video_deposit_metadata),
            headers=json_partial_project_headers,
        )
        # Should be forbidden (403) because user doesn't have upload permission
        assert resp.status_code == 403


def test_anonymous_user_has_upload_permission(app):
    """Test that anonymous users cannot upload."""
    with app.test_request_context():
        # No user logged in
        logout_user()

        # Test has_upload_permission function directly
        permission = Permission(upload_access_action)
        assert not permission.can()

        # Test has_upload_permission helper function
        assert not has_upload_permission()


def test_external_user_role_assignment(app, db, external_user):
    """Test that we can dynamically add cern-user role to external user."""
    with app.test_request_context():
        user = User.query.get(external_user)
        login_user(user)

        # Initially should not have upload permission
        assert not has_upload_permission()

        # Add cern-user role
        datastore = app.extensions["security"].datastore
        cern_user_role = Role.query.filter_by(name="cern-user").first()
        if not cern_user_role:
            cern_user_role = Role(name="cern-user")
            db.session.add(
                ActionRoles(action=upload_access_action.value, role=cern_user_role)
            )
        datastore.add_role_to_user(user, cern_user_role)
        db.session.commit()

        # Need to logout and login again for role to take effect
        logout_user()
        login_user(user)

        # Now should have upload permission
        assert has_upload_permission()


def test_published_video_access_control_external_user(
    api_app, location, users, external_user, api_project
):
    """Test external user access to published video records."""

    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Ensure external users have their email in identity for testing."""
        if (
            not isinstance(identity, AnonymousIdentity)
            and current_user.is_authenticated
        ):
            # Add UserNeed with email for all authenticated users (including external users)
            if (
                current_user.email
                and UserNeed(current_user.email) not in identity.provides
            ):
                identity.provides.add(UserNeed(current_user.email))

    (_, video_1, video_2) = api_project
    cern_user = User.query.filter_by(id=users[0]).first()
    user2 = User.query.filter_by(id=users[1]).first()
    ext_user = User.query.filter_by(id=external_user).first()

    # Prepare videos for publishing
    prepare_videos_for_publish([video_1, video_2])
    vid1 = video_1["_deposit"]["id"]
    vid2 = video_2["_deposit"]["id"]

    with api_app.test_client() as client:
        login_user(cern_user)

        # Create restricted video (user2 access only)
        video_1_metadata = dict(video_1)
        for key in ["_files"]:
            video_1_metadata.pop(key, None)
        video_1_metadata["_access"] = {"read": [user2.email]}

        resp = client.put(
            url_for("invenio_deposit_rest.video_item", pid_value=vid1),
            data=json.dumps(video_1_metadata),
            headers=[
                ("Content-Type", "application/vnd.video.partial+json"),
                ("Accept", "application/json"),
            ],
        )
        assert resp.status_code == 200

        # Publish restricted video
        url = url_for(
            "invenio_deposit_rest.video_actions", pid_value=vid1, action="publish"
        )
        assert client.post(url).status_code == 202
        rec_pid1, _ = deposit_video_resolver(vid1).fetch_published()

        # Create restricted video (external user access only)
        video_2_metadata = dict(video_2)
        for key in ["_files"]:
            video_2_metadata.pop(key, None)
        video_2_metadata["_access"] = {"read": [ext_user.email]}

        resp = client.put(
            url_for("invenio_deposit_rest.video_item", pid_value=vid2),
            data=json.dumps(video_2_metadata),
            headers=[
                ("Content-Type", "application/vnd.video.partial+json"),
                ("Accept", "application/json"),
            ],
        )
        assert resp.status_code == 200

        # Publish restricted video (external user access only)
        url = url_for(
            "invenio_deposit_rest.video_actions", pid_value=vid2, action="publish"
        )
        assert client.post(url).status_code == 202
        rec_pid2, _ = deposit_video_resolver(vid2).fetch_published()

        # Test external user access
        logout_user()
        login_user(ext_user)

        # External user should be blocked from video1
        resp1 = client.get(
            url_for("invenio_records_rest.recid_item", pid_value=rec_pid1.pid_value)
        )
        assert resp1.status_code in [403, 404]

        # External user should access video2
        resp2 = client.get(
            url_for("invenio_records_rest.recid_item", pid_value=rec_pid2.pid_value)
        )
        assert resp2.status_code == 200
        video_data = json.loads(resp2.data.decode("utf-8"))
        assert "metadata" in video_data


def test_external_user_deposit_operations(
    api_app,
    location,
    external_user,
    users,
    deposit_metadata,
    project_deposit_metadata,
    video_deposit_metadata,
    json_partial_project_headers,
    json_partial_video_headers,
):
    """Tests for external user deposit operations and permissions."""
    with api_app.test_request_context():
        # Setup: Create project and video as CERN user
        cern_user = User.query.get(users[0])
        login_user(cern_user)

        with api_app.test_client() as client:
            # Create project
            resp = client.post(
                url_for("invenio_deposit_rest.project_list"),
                data=json.dumps(project_deposit_metadata),
                headers=json_partial_project_headers,
            )
            assert resp.status_code == 201
            project_data = json.loads(resp.data.decode("utf-8"))
            project_id = project_data["metadata"]["_deposit"]["id"]

            # Create video
            video_deposit_metadata["_project_id"] = project_id
            resp = client.post(
                url_for("invenio_deposit_rest.video_list"),
                data=json.dumps(video_deposit_metadata),
                headers=json_partial_video_headers,
            )
            assert resp.status_code == 201
            video_data = json.loads(resp.data.decode("utf-8"))
            video_id = video_data["metadata"]["_deposit"]["id"]

            # Switch to external user for testing
            logout_user()
            ext_user = User.query.get(external_user)
            login_user(ext_user)

            # Test 1: Project creation - should be forbidden
            resp = client.post(
                url_for("invenio_deposit_rest.project_list"),
                data=json.dumps(deposit_metadata),
                headers=json_partial_project_headers,
            )
            assert resp.status_code == 403

            # Test 2: Project item operations - should be forbidden
            # GET project
            resp = client.get(
                url_for("invenio_deposit_rest.project_item", pid_value=project_id)
            )
            assert resp.status_code in [403, 404]

            # PUT project
            resp = client.put(
                url_for("invenio_deposit_rest.project_item", pid_value=project_id),
                data=json.dumps(deposit_metadata),
                headers=json_partial_project_headers,
            )
            assert resp.status_code == 403

            # DELETE project
            resp = client.delete(
                url_for("invenio_deposit_rest.project_item", pid_value=project_id)
            )
            assert resp.status_code == 403

            # Test 3: Project actions - should be forbidden
            actions = ["publish", "edit", "discard"]
            for action in actions:
                resp = client.post(
                    url_for(
                        "invenio_deposit_rest.project_actions",
                        pid_value=project_id,
                        action=action,
                    )
                )
                assert resp.status_code in [403, 404]

            # Test 4: File operations - should be forbidden
            # GET files list
            resp = client.get(
                url_for("invenio_deposit_rest.project_files", pid_value=project_id)
            )
            assert resp.status_code in [403, 404]

            # POST file upload
            resp = client.post(
                url_for("invenio_deposit_rest.project_files", pid_value=project_id),
                data={"file": (BytesIO(b"test content"), "test.txt")},
            )
            assert resp.status_code in [403, 404]

            # Test 5: Flows API - should be forbidden
            flow_payload = {
                "bucket_id": "test-bucket-id",
                "deposit_id": video_id,
                "key": "test-file.mp4",
                "version_id": "test-version-id",
            }
            resp = client.post(
                "/api/flows/",
                data=json.dumps(flow_payload),
                headers=json_partial_project_headers,
            )
            assert resp.status_code in [401, 403, 404]


def test_external_user_update_access_without_upload_permission(
    api_app, location, users, external_user, api_project
):
    """Test that external user in _access.update still can't edit without upload permission."""

    @identity_loaded.connect
    def mock_identity_provides(sender, identity):
        """Ensure external users have their email in identity for testing."""
        if (
            not isinstance(identity, AnonymousIdentity)
            and current_user.is_authenticated
        ):
            if (
                current_user.email
                and UserNeed(current_user.email) not in identity.provides
            ):
                identity.provides.add(UserNeed(current_user.email))

    (_, video_1, _) = api_project
    cern_user = User.query.get(users[0])
    ext_user = User.query.get(external_user)

    # Prepare videos for publishing
    prepare_videos_for_publish([video_1])
    vid1 = video_1["_deposit"]["id"]

    with api_app.test_client() as client:
        login_user(cern_user)

        # Create video with external user in update access
        video_1_metadata = dict(video_1)
        for key in ["_files"]:
            video_1_metadata.pop(key, None)
        video_1_metadata["_access"]["update"] = [ext_user.email]

        resp = client.put(
            url_for("invenio_deposit_rest.video_item", pid_value=vid1),
            data=json.dumps(video_1_metadata),
            headers=[
                ("Content-Type", "application/vnd.video.partial+json"),
                ("Accept", "application/json"),
            ],
        )
        # Publish video
        url = url_for(
            "invenio_deposit_rest.video_actions", pid_value=vid1, action="publish"
        )
        assert client.post(url).status_code == 202
        rec_pid1, _ = deposit_video_resolver(vid1).fetch_published()

        # Test external user (has update access but can't edit)
        logout_user()
        login_user(ext_user)

        # External user should be able to read the record
        resp = client.get(
            url_for("invenio_records_rest.recid_item", pid_value=rec_pid1.pid_value)
        )
        assert resp.status_code == 200
        video_data = json.loads(resp.data.decode("utf-8"))

        project_id = video_data["metadata"]["_project_id"]
        deposit_id = video_data["metadata"]["_deposit"]["id"]

        # External user should not be able to get the deposit
        resp = client.get(
            url_for("invenio_deposit_rest.project_item", pid_value=project_id)
        )
        assert resp.status_code in [403, 404]

        # External user should not be able to get the video deposit
        res = client.get(
            url_for("invenio_deposit_rest.video_item", pid_value=deposit_id)
        )
        assert res.status_code in [403, 404]

        # External user should not be able to edit the video
        url = url_for(
            "invenio_deposit_rest.video_actions", pid_value=deposit_id, action="edit"
        )
        assert client.post(url).status_code in [403, 404]
