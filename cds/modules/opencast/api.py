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
from datetime import datetime
from xml.etree import ElementTree

import requests
from cds.modules.opencast.error import RequestError
from cds.modules.xrootd.utils import file_opener_xrootd, file_size_xrootd
from flask import current_app
from invenio_files_rest.models import ObjectVersionTag
from requests_toolbelt import MultipartEncoder


class OpenCastRequestSession:
    def __init__(self, username, password, verify_cert=True):
        """Constructor."""
        self.username = username
        self.password = password
        self.verify_cert = verify_cert

    def __enter__(self):
        self.session = requests.Session()
        self.session.auth = (
            self.username,
            self.password,
        )
        self.session.verify = self.verify_cert
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


class OpenCast:
    def __init__(self, video, object_version):
        """Constructor."""
        self.video = video
        self.object_version = object_version
        self.BASE_URL = current_app.config["CDS_OPENCAST_API_ENDPOINT_INGEST"]

        module_dir = os.path.dirname(__file__)
        self.acl_filepath = os.path.join(module_dir, "static/xml/acl.xml")

    def run(self, qualities):
        """Submit workflow to OpenCast."""
        session_context = OpenCastRequestSession(
            current_app.config["CDS_OPENCAST_API_USERNAME"],
            current_app.config["CDS_OPENCAST_API_PASSWORD"],
            current_app.config["CDS_OPENCAST_API_ENDPOINT_VERIFY_CERT"],
        )
        with session_context as session:
            opencast_event_id, mp_xml = self._create_media_package(session)
            new_mp_xml = self._add_metadata(session, mp_xml, qualities)
            new_mp_xml = self._add_track(session, new_mp_xml)
            new_mp_xml = self._add_acl(session, new_mp_xml)
            self._ingest(session, new_mp_xml, qualities)

        return opencast_event_id

    def _create_media_package(self, session):
        """Creates the media package and returns the event_id."""
        url = self.BASE_URL + "/createMediaPackage"
        current_app.logger.info(
            "Opencast request for media package creation: {0}".format(url)
        )
        try:
            response = session.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestError(url, e)
        # get the media package id, which is also the event id
        tree = ElementTree.fromstring(response.content)
        media_package_id = tree.attrib["id"]
        return media_package_id, response.content

    def _add_metadata(self, session, media_package_xml, qualities):
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
                <dcterms:description>{description}</dcterms:description>
                <dcterms:subject>cds videos</dcterms:subject>
                <dcterms:language>eng</dcterms:language>
                <dcterms:spatial>Remote</dcterms:spatial>
                <dcterms:title>{title}</dcterms:title>
                <dcterms:isPartOf>{series_id}</dcterms:isPartOf>
        </dublincore>
        """
        label_project = "CDS Videos"
        label_title = self.video.get("title", {}).get("title", "")
        record_pid = self.video["_deposit"].get("pid")
        label_record = "recid: {0}" if record_pid else ""
        label_deposit = "depid: {0}".format(self.video["_deposit"]["id"])
        title = " - ".join(
            x for x in [label_project, label_title, label_record, label_deposit] if x
        )

        description = """{title} - {deposit} - object version: {object_version} - qualities: {qualities}""".format(
            title=label_title,
            deposit=label_deposit,
            object_version=self.object_version.version_id,
            qualities=" - ".join(qualities),
        )

        now = datetime.utcnow()
        start = now.strftime("%Y-%m-%dT%H:%M:%S")
        form_data = dict(
            mediaPackage=media_package_xml,
            flavor="dublincore/episode",
            dublinCore=xml_metadata.format(
                start=start,
                series_id=current_app.config["CDS_OPENCAST_SERIES_ID"],
                title=title,
                description=description,
            ),
        )

        url = self.BASE_URL + "/addDCCatalog"
        current_app.logger.info(
            "Opencast request for adding metadata: {0}".format(url)
        )
        try:
            response = session.post(url, data=form_data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestError(url, e)
        return response.content

    def _add_track(self, session, media_package_xml):
        """Adds track to the media package."""
        video_filepath = self.object_version.file.uri
        video_filename = self.object_version.key

        url = self.BASE_URL + "/addTrack"
        current_app.logger.info(
            "Opencast request for adding track: {0}".format(url)
        )
        data = MultipartEncoder(
            fields=dict(
                mediaPackage=media_package_xml,
                flavor="presenter/source",
                file=(
                    video_filename,
                    file_opener_xrootd(video_filepath, "rb"),
                ),
            )
        )
        start = time.time()
        try:
            response = session.post(
                url,
                data=data,
                headers={"Content-Type": data.content_type},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestError(url, e)
        end = time.time()

        size = file_size_xrootd(video_filepath)
        ObjectVersionTag.create_or_update(
            self.object_version,
            "file_upload_time_in_seconds",
            str(int(end - start)),
        )
        ONE_MB = 0.000001
        ObjectVersionTag.create_or_update(
            self.object_version, "file_size_mb", str(size * ONE_MB)
        )

        return response.content

    def _add_acl(self, session, media_package_xml):
        """Adds required acl file to the media package."""
        url = self.BASE_URL + "/addAttachment"
        current_app.logger.info(
            "Opencast request for adding acl file: {0}".format(url)
        )
        form_data = dict(
            mediaPackage=media_package_xml, flavor="security/xacml+episode"
        )

        with open(self.acl_filepath, "rb") as f:
            files = dict(acl=f)
            try:
                response = session.post(url, files=files, data=form_data)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise RequestError(url, e)
            return response.content

    def _ingest(self, session, media_package_xml, qualities):
        """Triggers transcoding of subformats."""
        form_data = dict(mediaPackage=media_package_xml)
        for quality in current_app.config["CDS_OPENCAST_QUALITIES"].keys():
            if quality not in qualities:
                dict_key = "flagQuality{0}".format(quality)
                form_data.update({dict_key: "false"})

        url = self.BASE_URL + "/ingest/cern-cds-videos"
        current_app.logger.info(
            "Opencast request for ingesting (qualities {0}): {1}".format(
                qualities, url
            )
        )
        try:
            response = session.post(url, data=form_data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RequestError(url, e)
        return response.content
