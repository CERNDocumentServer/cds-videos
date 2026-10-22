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

"""Storage class that offloads file downloads to EOS via nginx.

Only downloads served by the ``invenio-files-rest`` object endpoint
(``/api/files/<bucket>/<key>``) are offloaded. The storage resolves the physical
EOS URL for the requested file (authenticating against the EOS HTTP gateway with
X.509 or Kerberos) and returns an empty response carrying an ``X-Accel-Redirect``
header; nginx then streams the bytes straight from EOS to the client, freeing the
uWSGI worker. Video streaming is served by a separate streaming server and never
reaches files-rest, so it is unaffected.

On any error the storage falls back to normal in-app streaming, so a
misconfiguration or an EOS hiccup never produces a user-visible download failure.
"""

import mimetypes
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit

import requests
from flask import current_app, has_request_context, make_response, request
from invenio_files_rest.helpers import sanitize_mimetype
from invenio_files_rest.storage.pyfs import pyfs_storage_factory

try:
    from invenio_xrootd.storage import EOSFileStorage as BaseFileStorage
except ImportError:
    # XRootD not available (e.g. local/dev without the client): fall back to the
    # plain filesystem storage so the class can still be imported and used.
    from invenio_files_rest.storage.pyfs import PyFSFileStorage as BaseFileStorage

try:
    from requests_kerberos import DISABLED, HTTPKerberosAuth
except ImportError:
    # Kerberos support is optional (X.509 is the default auth method).
    HTTPKerberosAuth = None
    DISABLED = 3

#: Files-rest endpoints whose downloads are offloaded to EOS. Overridable via the
#: ``CDS_EOS_OFFLOAD_ENDPOINTS`` config to add/remove entry points without a code
#: change.
DEFAULT_OFFLOAD_ENDPOINTS = ("invenio_files_rest.object_api",)


class OffloadEOSFileStorage(BaseFileStorage):
    """Offload file downloads to nginx via an ``X-Accel-Redirect`` to EOS."""

    def _get_auth_session(self):
        """Return a requests session authenticated against the EOS gateway.

        Uses X.509 when ``CDS_EOS_OFFLOAD_AUTH_X509`` is set and a cert/key pair
        is configured, otherwise falls back to Kerberos.
        """
        session = requests.Session()
        session.verify = False

        x509_enabled = current_app.config.get("CDS_EOS_OFFLOAD_AUTH_X509", False)
        cert = current_app.config.get("CDS_EOS_OFFLOAD_X509_CERT_PATH")
        key = current_app.config.get("CDS_EOS_OFFLOAD_X509_KEY_PATH")

        if x509_enabled and cert and key:
            session.cert = (cert, key)
        elif HTTPKerberosAuth is not None:
            session.auth = HTTPKerberosAuth(DISABLED)
        else:
            raise RuntimeError(
                "EOS offload authentication not configured: X.509 disabled and "
                "requests-kerberos is not installed."
            )
        return session

    def _get_eos_redirect_path(self):
        """Resolve the real EOS URL and build the ``X-Accel-Redirect`` path."""
        host = current_app.config["CDS_EOS_OFFLOAD_HTTPHOST"]
        redirect_base_path = current_app.config["CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH"]

        # ``self.fileurl`` is an XRootD URL (``root://host//eos/...``); its path
        # starts with a double slash, so normalise to a single leading slash.
        base_path = urlsplit(self.fileurl).path.lstrip("/")

        session = self._get_auth_session()
        eos_resp = session.get(
            "{host}/{path}".format(host=host.rstrip("/"), path=base_path),
            allow_redirects=False,
            timeout=current_app.config.get("CDS_EOS_OFFLOAD_TIMEOUT", 5),
        )
        if eos_resp.status_code != 307:
            raise Exception(
                "EOS redirect failed with response code: {code} and error: {text}".format(
                    code=eos_resp.status_code, text=eos_resp.text
                )
            )

        eos_url_parts = urlsplit(eos_resp.next.url)
        # Strip the leading slash of the EOS path so that nginx (which inserts a
        # slash before the captured path) reconstructs a clean single-slash URL.
        redirect_path = "{base}/{scheme}/{host}/{port}/{path}".format(
            base=redirect_base_path,
            scheme=eos_url_parts.scheme,
            host=eos_url_parts.hostname,
            port=eos_url_parts.port,
            path=eos_url_parts.path.lstrip("/"),
        )
        return urlunsplit(("", "", redirect_path, eos_url_parts.query, ""))

    def _should_offload(self):
        """Whether the current request should be offloaded to EOS.

        Important: this relies on ``FILES_REST_XSENDFILE_ENABLED`` being left
        **False**. When that flag is True, invenio-files-rest's own xsendfile
        handler short-circuits ``ObjectResource.get`` to
        ``FILES_REST_XSENDFILE_RESPONSE_FUNC`` (which redirects to
        ``/user_files/``) *before* the storage layer is reached, so this method
        never runs. Our offload lives entirely in the storage ``send_file`` and
        is controlled solely by ``CDS_EOS_OFFLOAD_ENABLED``.
        """
        if not has_request_context():
            return False
        if not current_app.config.get("CDS_EOS_OFFLOAD_ENABLED", False):
            return False
        # Never offload HEAD (used by the player to probe size); only GET.
        if request.method != "GET":
            return False
        endpoints = current_app.config.get(
            "CDS_EOS_OFFLOAD_ENDPOINTS", DEFAULT_OFFLOAD_ENDPOINTS
        )
        return request.endpoint in endpoints

    def send_file(
        self,
        filename,
        mimetype=None,
        restricted=True,
        checksum=None,
        trusted=False,
        chunk_size=None,
        as_attachment=False,
        **kwargs
    ):
        """Send the file, offloading the download to EOS when applicable."""
        if not self._should_offload():
            return super().send_file(
                filename,
                mimetype=mimetype,
                restricted=restricted,
                checksum=checksum,
                trusted=trusted,
                chunk_size=chunk_size,
                as_attachment=as_attachment,
            )

        try:
            redirect_path = self._get_eos_redirect_path()
        except Exception as ex:
            current_app.logger.exception(ex)
            # Fall back to streaming the file through the application.
            return super().send_file(
                filename,
                mimetype=mimetype,
                restricted=restricted,
                checksum=checksum,
                trusted=trusted,
                chunk_size=chunk_size,
                as_attachment=as_attachment,
            )

        response = make_response()
        response.headers["X-Accel-Redirect"] = redirect_path
        response.headers["X-Accel-Buffering"] = "yes"
        response.headers["X-Accel-Limit-Rate"] = "off"

        mimetype = mimetypes.guess_type(filename)[0]
        if mimetype is not None:
            mimetype = sanitize_mimetype(mimetype, filename=filename)
        if mimetype is None:
            mimetype = "application/octet-stream"
        response.mimetype = mimetype

        # Force Content-Disposition for application/octet-stream to prevent
        # Content-Type sniffing (from invenio-files-rest). ``filename`` reflects
        # any download-time renaming done by the file_downloaded receiver.
        if as_attachment or mimetype == "application/octet-stream":
            try:
                filename.encode("ascii")
            except UnicodeEncodeError:
                simple = unicodedata.normalize("NFKD", filename)
                simple = simple.encode("ascii", "ignore").decode("ascii")
                quoted = quote(filename, safe="!#$&+-.^_`|~")
                filenames = {"filename": simple, "filename*": "UTF-8''{0}".format(quoted)}
            else:
                filenames = {"filename": filename}
            response.headers.set("Content-Disposition", "attachment", **filenames)
        else:
            response.headers.set("Content-Disposition", "inline")

        # Security-related headers for the download (from invenio-files-rest).
        response.headers["Content-Security-Policy"] = "default-src 'none';"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Frame-Options"] = "deny"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Marker header to track offloaded responses.
        response.headers["Invenio-Offload"] = "true"
        return response


def offload_storage_factory(**kwargs):
    """Storage factory enabling EOS download offloading."""
    return pyfs_storage_factory(filestorage_class=OffloadEOSFileStorage, **kwargs)
