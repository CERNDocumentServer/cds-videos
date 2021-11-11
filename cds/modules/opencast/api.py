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
import time

import requests
from xml.etree import ElementTree
from flask import current_app
from invenio_files_rest.models import ObjectVersionTag
from requests_toolbelt import MultipartEncoder

from cds.modules.opencast.error import RequestError
from cds.modules.xrootd.utils import file_opener_xrootd, file_size_xrootd
from datetime import datetime, timedelta


def _create_media_package(session):
    """Creates the media package and returns the event_id."""
    url = "{endpoint}/createMediaPackage".format(
        endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
    )
    try:
        response = session.get(
            url,
            verify=current_app.config['CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT']
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RequestError(url, e.message)
    # get the media package id, which is also the event id
    tree = ElementTree.fromstring(response.content)
    media_package_id = tree.attrib["id"]
    return media_package_id, response.content


def _add_acl(media_package_xml, acl_filepath, session):
    """Adds required acl file to the media package."""
    url = "{endpoint}/addAttachment".format(
        endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
    )
    form_data = dict(
        mediaPackage=media_package_xml,
        flavor="security/xacml+episode"
    )

    with open(acl_filepath, "rb") as f:
        files = dict(
            acl=f
        )
        try:
            response = session.post(
                url,
                files=files,
                data=form_data,
                verify=current_app.config[
                    'CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT'
                ]
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestError(url, e.message)
        return response.content


def _add_metadata(media_package_xml, object_version, session):
    """Adds metadata to the media package."""
    xml_metadata = """<?xml version="1.0" encoding="UTF-8" ?>
    <dublincore
        xmlns="http://www.opencastproject.org/xsd/1.0/dublincore/"
        xmlns:dcterms="http://purl.org/dc/terms/"
        xmlns:oc="http://www.opencastproject.org/matterhorn/"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <dcterms:creator>CDS Videos</dcterms:creator>
            <dcterms:contributor>No contributor</dcterms:contributor>
            <dcterms:created>{start}</dcterms:created>
            <dcterms:description>descr - CDS Videos test</dcterms:description>
            <dcterms:subject>cds videos</dcterms:subject>
            <dcterms:language>eng</dcterms:language>
            <dcterms:spatial>Remote</dcterms:spatial>
            <dcterms:title>ObjectVersion version_id: {version_id}</dcterms:title>
            <dcterms:isPartOf>{series_id}</dcterms:isPartOf>
    </dublincore>
    """
    now = datetime.utcnow()
    start = now.strftime("%Y-%m-%dT%H:%M:%S")
    form_data = dict(
        mediaPackage=media_package_xml,
        flavor="dublincore/episode",
        dublinCore=xml_metadata.format(
            start=start,
            series_id=current_app.config['CDS_OPENCAST_SERIES_ID_TEST'],
            version_id=object_version.version_id
        ),
    )
    url = "{endpoint}/addDCCatalog".format(
        endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
    )
    try:
        response = session.post(
            url,
            data=form_data,
            verify=current_app.config['CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT']
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RequestError(url, e.message)
    return response.content


def _add_track(
        media_package_xml,
        video_filepath,
        video_filename,
        session,
        object_version
):
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
    url = "{endpoint}/addTrack".format(
        endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
    )
    start = time.time()
    try:
        response = session.post(
            url,
            data=data,
            headers={'Content-Type': data.content_type},
            verify=current_app.config['CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT']
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RequestError(url, e.message)
    end = time.time()
    size = file_size_xrootd(video_filepath)
    ObjectVersionTag.create_or_update(
        object_version, 'file_upload_time_in_seconds', str(int(end-start))
    )
    ObjectVersionTag.create_or_update(
        object_version, 'file_size_mb', str(size*0.000001)
    )

    return response.content


def _ingest(media_package_xml, qualities, session):
    """Triggers transcoding of subformats."""
    form_data = dict(
        mediaPackage=media_package_xml,
    )

    url = "{endpoint}/ingest/cern-cds-videos".format(
        endpoint=current_app.config['CDS_OPENCAST_API_ENDPOINT_INGEST']
    )

    for quality in current_app.config['CDS_OPENCAST_QUALITIES'].keys():
        if quality not in qualities:
            dict_key = 'flagQuality{0}'.format(quality)
            form_data.update({dict_key: "false"})

    try:
        response = session.post(
            url,
            data=form_data,
            verify=current_app.config['CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT']
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RequestError(url, e.message)
    return response.content


def start_workflow(object_version, qualities):
    """Starts opencast workflow."""
    session = requests.Session()
    session.auth = (
        current_app.config['CDS_OPENCAST_API_USERNAME'],
        current_app.config['CDS_OPENCAST_API_PASSWORD']
    )
    video_filepath = object_version.file.uri
    video_filename = object_version.key
    module_dir = os.path.dirname(__file__)
    acl_filepath = os.path.join(module_dir, "static/xml/acl.xml")
    event_id, mp_xml = _create_media_package(session)
    new_mp_xml = _add_metadata(mp_xml, object_version, session)
    new_mp_xml = _add_track(
        new_mp_xml, video_filepath, video_filename, session, object_version
    )
    new_mp_xml = _add_acl(new_mp_xml, acl_filepath, session)
    _ingest(new_mp_xml, qualities, session)
    session.close()
    return event_id
