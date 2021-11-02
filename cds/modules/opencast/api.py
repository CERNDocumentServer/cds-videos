# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2021 CERN.
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

"""Opencast API."""
import os

import requests
from xml.etree import ElementTree
from flask import current_app
from requests_toolbelt import MultipartEncoder

from cds.modules.xrootd.utils import file_opener_xrootd
from datetime import datetime, timedelta


def _create_media_package(session):
    """Creates the media package and returns the event_id."""
    r = session.get(
        "{endpoint}/createMediaPackage".format(
            endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
        ),
        verify=False
    )

    # get the media package id, which is also the event id
    tree = ElementTree.fromstring(r.content)
    media_package_id = tree.attrib["id"]
    return media_package_id, r.content


def _add_acl(media_package_xml, acl_filepath, session):
    """Adds required acl file to the media package."""
    form_data = dict(
        mediaPackage=media_package_xml,
        flavor="security/xacml+episode"
    )
    with open(acl_filepath, "rb") as f:
        files = dict(
            acl=f
        )
        r = session.post(
            "{endpoint}/addAttachment".format(
                endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
            ), files=files,
            data=form_data,
            verify=False
        )
        return r.content


def _add_metadata(media_package_xml, object_version, session):
    """Adds metadata to the media package."""
    now = datetime.utcnow()
    start = now.strftime("%Y-%m-%dT%H:%M:%S")
    end = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    xml_metadata = current_app.config['CDS_OPENCAST_METADATA']
    form_data = dict(
        mediaPackage=media_package_xml,
        flavor="dublincore/episode",
        dublinCore=xml_metadata.format(
            start=start,
            end=end,
            series_id=current_app.config['CDS_OPENCAST_SERIES_ID_TEST'],
            version_id=object_version.version_id
        ),
    )
    r = session.post(
        "{endpoint}/addDCCatalog".format(
            endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
        ),
        data=form_data,
        verify=False
    )
    return r.content


def _add_track(media_package_xml, video_filepath, video_filename, session):
    """Adds track to the media package."""

    data = MultipartEncoder(
        fields=dict(
            mediaPackage=media_package_xml,
            flavor="presenter/source",
            file=(
                video_filename,
                file_opener_xrootd(video_filepath, 'rb')
            )
        )
    )

    r = session.post(
        "{endpoint}/addTrack".format(
            endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
        ),
        data=data,
        headers={'Content-Type': data.content_type},
        verify=False
    )

    return r.content


def _ingest(media_package_xml, qualities, session):
    """Triggers transcoding of subformats."""
    form_data = dict(
        mediaPackage=media_package_xml,
    )
    for quality in current_app.config['CDS_OPENCAST_QUALITIES'].keys():
        if quality not in qualities:
            dict_key = 'flagQuality{0}'.format(quality)
            form_data.update({dict_key: "false"})
    r = session.post(
        "{endpoint}/ingest/cern-cds-videos".format(
            endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
        ),
        data=form_data,
        verify=False
    )
    return r.content


def start_workflow(object_version, qualities):
    """Starts opencast workflow."""
    session = requests.Session()
    session.auth = (
        current_app.config['CDS_OPENCAST_API_USERNAME'],
        current_app.config['CDS_OPENCAST_API_PASSWORD']
    )
    video_filepath = object_version.file.uri
    video_filename = object_version.key
    script_dir = os.path.dirname(__file__)
    acl_filepath = os.path.join(script_dir, "static/xml/acl.xml")
    event_id, mp_xml = _create_media_package(session)
    new_mp_xml = _add_metadata(mp_xml, object_version, session)
    new_mp_xml = _add_track(new_mp_xml, video_filepath, video_filename, session)
    new_mp_xml = _add_acl(new_mp_xml, acl_filepath, session)
    _ingest(new_mp_xml, qualities, session)
    session.close()
    return event_id
