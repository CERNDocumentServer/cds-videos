# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2026 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CERN Document Server is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CERN Document Server; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Tests for the EOS download offload storage."""

from contextlib import contextmanager
from unittest import mock

import pytest

from cds.modules.xrootd import storage as storage_mod
from cds.modules.xrootd.storage import OffloadEOSFileStorage

FILEURL = "root://eosmedia.cern.ch//eos/media/cds/test/videos/files/ab/cd/uuid/data"


@contextmanager
def offload_request(app, method="GET", endpoint="invenio_files_rest.object_api",
                    enabled=True):
    """App+request context with offload config and a patched request."""
    app.config.update(
        CDS_EOS_OFFLOAD_ENABLED=enabled,
        CDS_EOS_OFFLOAD_HTTPHOST="https://eosmedia.cern.ch:8444",
        CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH="/eos_storage",
        CDS_EOS_OFFLOAD_ENDPOINTS=["invenio_files_rest.object_api"],
    )
    with app.test_request_context():
        with mock.patch.object(storage_mod, "has_request_context", return_value=True), \
                mock.patch.object(storage_mod, "request") as m_req:
            m_req.method = method
            m_req.endpoint = endpoint
            yield


def _storage():
    return OffloadEOSFileStorage(FILEURL)


def test_no_offload_when_disabled(app):
    """Offload disabled -> delegate to the base storage."""
    storage = _storage()
    with offload_request(app, enabled=False), \
            mock.patch.object(storage_mod.BaseFileStorage, "send_file",
                              return_value="BASE") as base:
        assert storage.send_file("data") == "BASE"
    base.assert_called_once()


def test_offload_independent_of_xsendfile(app):
    """The storage offload must not depend on FILES_REST_XSENDFILE_ENABLED.

    On files-rest 2.x that flag triggers files-rest's own ``/user_files/``
    xsendfile at the view level (bypassing this storage), so our offload is
    driven solely by ``CDS_EOS_OFFLOAD_ENABLED`` and works with it left False.
    """
    storage = _storage()
    app.config.update(FILES_REST_XSENDFILE_ENABLED=False)
    with offload_request(app), \
            mock.patch.object(OffloadEOSFileStorage, "_get_eos_redirect_path",
                              return_value="/eos_storage/x"):
        resp = storage.send_file("data")
    assert resp.headers["Invenio-Offload"] == "true"


def test_no_offload_for_head(app):
    """HEAD requests are never offloaded (player probes)."""
    storage = _storage()
    with offload_request(app, method="HEAD"), \
            mock.patch.object(storage_mod.BaseFileStorage, "send_file",
                              return_value="BASE") as base:
        assert storage.send_file("data") == "BASE"
    base.assert_called_once()


def test_no_offload_for_other_endpoint(app):
    """Only the files-rest download endpoint is offloaded."""
    storage = _storage()
    with offload_request(app, endpoint="invenio_records_ui.recid"), \
            mock.patch.object(storage_mod.BaseFileStorage, "send_file",
                              return_value="BASE") as base:
        assert storage.send_file("data") == "BASE"
    base.assert_called_once()


def test_offload_returns_xaccel_redirect(app):
    """A download on /api/files returns an X-Accel-Redirect response."""
    storage = _storage()
    redirect = "/eos_storage/https/eosfst01.cern.ch/1095//eos/media/x/data?authz=TOKEN"
    # Use a whitelisted (inline-able) mime type, mocked so the assertion does not
    # depend on the system mime db. Note: non-whitelisted types (e.g. video/mp4)
    # are sanitized to application/octet-stream and served as attachments.
    with offload_request(app), \
            mock.patch.object(storage_mod.mimetypes, "guess_type",
                              return_value=("image/png", None)), \
            mock.patch.object(OffloadEOSFileStorage, "_get_eos_redirect_path",
                              return_value=redirect):
        resp = storage.send_file("poster.png")
    assert resp.headers["X-Accel-Redirect"] == redirect
    assert resp.headers["Invenio-Offload"] == "true"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Content-Disposition"] == "inline"
    assert resp.mimetype == "image/png"


def test_offload_attachment_disposition(app):
    """Unknown mimetype is forced to an attachment download."""
    storage = _storage()
    with offload_request(app), \
            mock.patch.object(OffloadEOSFileStorage, "_get_eos_redirect_path",
                              return_value="/eos_storage/x"):
        resp = storage.send_file("data", as_attachment=True)
    assert resp.mimetype == "application/octet-stream"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert "filename=data" in resp.headers["Content-Disposition"]


def test_offload_falls_back_on_eos_error(app):
    """Any EOS resolution error falls back to in-app streaming."""
    storage = _storage()
    with offload_request(app), \
            mock.patch.object(OffloadEOSFileStorage, "_get_eos_redirect_path",
                              side_effect=Exception("EOS down")), \
            mock.patch.object(storage_mod.BaseFileStorage, "send_file",
                              return_value="BASE") as base:
        assert storage.send_file("data") == "BASE"
    base.assert_called_once()


def test_redirect_path_from_307(app):
    """The X-Accel-Redirect path is built from the EOS 307 target."""
    storage = _storage()
    eos_resp = mock.Mock(status_code=307)
    eos_resp.next.url = (
        "https://eosfst01.cern.ch:1095/eos/media/cds/test/videos/files/ab/cd/uuid/data"
        "?authz=TOKEN"
    )
    session = mock.Mock()
    session.get.return_value = eos_resp
    with app.app_context():
        app.config.update(
            CDS_EOS_OFFLOAD_HTTPHOST="https://eosmedia.cern.ch:8444",
            CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH="/eos_storage",
        )
        with mock.patch.object(storage, "_get_auth_session", return_value=session):
            path = storage._get_eos_redirect_path()
    # Gateway queried with the normalised single-slash path.
    session.get.assert_called_once()
    called_url = session.get.call_args[0][0]
    assert called_url == (
        "https://eosmedia.cern.ch:8444/eos/media/cds/test/videos/files/ab/cd/uuid/data"
    )
    assert path == (
        "/eos_storage/https/eosfst01.cern.ch/1095/eos/media/cds/test/videos/files/"
        "ab/cd/uuid/data?authz=TOKEN"
    )


def test_redirect_path_raises_on_non_307(app):
    """A non-307 gateway response raises (caller falls back)."""
    storage = _storage()
    session = mock.Mock()
    session.get.return_value = mock.Mock(status_code=403, text="Operation not permitted")
    with app.app_context():
        app.config.update(
            CDS_EOS_OFFLOAD_HTTPHOST="https://eosmedia.cern.ch:8444",
            CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH="/eos_storage",
        )
        with mock.patch.object(storage, "_get_auth_session", return_value=session):
            with pytest.raises(Exception):
                storage._get_eos_redirect_path()


def test_auth_session_x509(app):
    """X.509 auth configures the client certificate on the session."""
    storage = _storage()
    with app.app_context():
        app.config.update(
            CDS_EOS_OFFLOAD_AUTH_X509=True,
            CDS_EOS_OFFLOAD_X509_CERT_PATH="/etc/certificates/cert.pem",
            CDS_EOS_OFFLOAD_X509_KEY_PATH="/etc/certificates/key.pem",
        )
        session = storage._get_auth_session()
    assert session.cert == ("/etc/certificates/cert.pem", "/etc/certificates/key.pem")
    assert session.verify is False


def test_auth_session_kerberos(app):
    """Without X.509, Kerberos auth is used when available."""
    storage = _storage()
    with app.app_context():
        app.config.update(CDS_EOS_OFFLOAD_AUTH_X509=False)
        with mock.patch.object(storage_mod, "HTTPKerberosAuth") as krb:
            session = storage._get_auth_session()
    assert session.auth == krb.return_value


def test_auth_session_misconfigured_raises(app):
    """No X.509 and no Kerberos -> explicit error."""
    storage = _storage()
    with app.app_context():
        app.config.update(CDS_EOS_OFFLOAD_AUTH_X509=False)
        with mock.patch.object(storage_mod, "HTTPKerberosAuth", None):
            with pytest.raises(RuntimeError):
                storage._get_auth_session()
