# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# Invenio-RDM is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.


from io import BytesIO

import pytest
from invenio_pidstore.models import PersistentIdentifier
from cds.modules.legacy.minters import legacy_recid_minter
from invenio_db import db

LEGACY_RECID = "123456"
LEGACY_RECID_PID_TYPE = "lrecid"

def test_legacy_record_redirection(app, video_published):
    """Test legacy redirection mechanism."""
    
    with app.test_client() as client:
        # Fetch published record and its UUID
        recid_pid, _ = video_published.fetch_published()
        record_uuid = str(recid_pid.object_uuid)

        # Mint legacy PID
        legacy_recid_minter(LEGACY_RECID, record_uuid)
        db.session.commit() 

        # Expected redirection target
        expected_location = f"{app.config['SITE_URL']}/record/{recid_pid.pid_value}"

        # Test redirection from legacy recid
        url = f"/legacy/record/{LEGACY_RECID}"
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 301
        assert response.location == expected_location

        # Optionally follow the redirect if the final destination is also handled
        response = client.get(url, follow_redirects=True)
        assert response.status_code == 200

        # Test not found for unknown recid
        response = client.get("/legacy/record/654321")
        assert response.status_code == 404

