# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016, 2017, 2018, 2020 CERN.
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
"""Celery tasks for Webhook Receivers."""

from __future__ import absolute_import

import json
import logging
import os
import shutil
import signal
import tempfile
import time

import jsonpatch
import requests
from celery import Task as _Task
from celery import current_app as celery_app
from celery import shared_task
from celery.result import AsyncResult
from celery.task.control import revoke
from celery.utils.log import get_task_logger
from flask import current_app
from flask_iiif.utils import create_gif_from_frames
from invenio_db import db
from invenio_files_rest.models import (ObjectVersion, ObjectVersionTag,
                                       as_bucket, as_object_version)
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from PIL import Image
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import ConcurrentModificationError
from werkzeug.utils import import_string

from cds.modules.flows.models import FlowTaskMetadata
from cds.modules.flows.models import FlowTaskStatus as FlowTaskStatus

from ..ffmpeg import ff_frames, ff_probe_all
from ..opencast.api import OpenCast
from ..opencast.error import RequestError
from ..opencast.utils import get_qualities
from ..records.utils import to_string
from ..xrootd.utils import file_opener_xrootd
from .deposit import index_deposit_project
from .files import dispose_object_version, move_file_into_local

logger = get_task_logger(__name__)


class CeleryTask(_Task):
    """The task class which is used as the minimal unit of work.

    This class is a wrapper around ``celery.Task``
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Update task status on database."""
        with celery_app.flask_app.app_context():
            for (
                flow_task_metadata
            ) in FlowTaskMetadata.get_all_by_flow_task_name(
                self.flow_id, self.name
            ):
                flow_task_metadata.status = FlowTaskStatus.FAILURE
                flow_task_metadata.message = str(einfo)
            db.session.commit()

        super(CeleryTask, self).on_failure(exc, task_id, args, kwargs, einfo)

        self._reindex_video_project()

    def on_success(self, retval, task_id, args, kwargs):
        """Update tasks status on database."""
        with celery_app.flask_app.app_context():
            for (
                flow_task_metadata
            ) in FlowTaskMetadata.get_all_by_flow_task_name(
                self.flow_id, self.name
            ):
                flow_task_metadata.status = FlowTaskStatus.SUCCESS
                flow_task_metadata.message = "{}".format(retval)
            db.session.commit()

        super(CeleryTask, self).on_success(retval, task_id, args, kwargs)

        self._reindex_video_project()

    @staticmethod
    def stop_task(celery_task_id):
        """Stop singular task."""
        revoke(str(celery_task_id), terminate=True, signal="SIGKILL")
        result = AsyncResult(str(celery_task_id))
        result.forget()


class AVCTask(CeleryTask):
    """Base class for tasks."""

    abstract = True

    _base_payload = {}

    def _pop_call_arguments(self, arg_list, **kwargs):
        for name in arg_list:
            setattr(self, name, kwargs.pop(name))
        return kwargs

    def __call__(self, *args, **kwargs):
        """Extract keyword arguments."""
        arg_list = ["flow_id", "deposit_id", "key"]
        kwargs = self._pop_call_arguments(arg_list, **kwargs)
        with self.app.flask_app.app_context():
            if kwargs.get("_clean", False):
                self.clean(*args, **kwargs)

            self.object_version = as_object_version(
                kwargs.pop("version_id", None)
            )
            self.object_version_id = str(self.object_version.version_id)
            self.set_base_payload()

            return self.run(*args, **kwargs)

    def log(self, msg):
        """Log message."""
        _msg = "Celery task `{ct}` - Flow {flow}: {msg}".format(
            ct=self.name, flow=self.flow_id, msg=msg
        )
        current_app.logger.debug(_msg)

    def _meta_exception_envelope(self, exc):
        """Create a envelope for exceptions.

        NOTE: workaround to be able to save the payload in celery in case of
        exceptions.
        """
        meta = dict(message=str(exc), payload=self._base_payload)
        return dict(exc_message=meta, exc_type=exc.__class__.__name__)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """When an error occurs, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            exception = self._meta_exception_envelope(exc=exc)
            self._reindex_video_project()
            self.log("Failure: {0}".format(exception))

        super(AVCTask, self).on_failure(
            exc=exc, task_id=task_id, args=args, kwargs=kwargs, einfo=einfo
        )

    def on_success(self, exc, task_id, args, kwargs):
        """When end correctly, attach useful information to the state."""
        with celery_app.flask_app.app_context():
            meta = dict(message=str(exc), payload=self._base_payload)
            self._reindex_video_project()
            self.log("Success: {0}".format(meta))

        super(AVCTask, self).on_success(
            retval=exc, task_id=task_id, args=args, kwargs=kwargs
        )

    def _reindex_video_project(self):
        """Reindex video and project."""
        with celery_app.flask_app.app_context():
            deposit_id = self._base_payload["deposit_id"]
            index_deposit_project(deposit_id)

    @staticmethod
    def set_revoke_handler(handler):
        """Set handler to be executed when the task gets revoked."""

        def _handler(signum, frame):
            with celery_app.flask_app.app_context():
                handler()

        signal.signal(signal.SIGTERM, _handler)

    def set_base_payload(self):
        """Set default base payload."""
        self._base_payload = dict(
            deposit_id=self.deposit_id,
            flow_id=self.flow_id,
            name=self.name,
            key=self.key,
            tags=self.object_version.get_tags(),
            master_id=self.object_version_id,
        )

    def get_full_payload(self, **kwargs):
        """Get full payload merging base payload and kwargs."""
        _payload = dict()

        # base payload EXAMPLE
        # {'deposit_id': <value>, 'tags':
        #   {u'context_type': u'master', u'media_type': u'video',
        #    u'preview': u'true', u'flow_id': <value>},
        # 'name': <celery task name>,
        # 'master_version_id': <value>,
        # 'flow_id': <value>,
        # 'key': <value>}
        _payload.update(self._base_payload)

        # kwargs EXAMPLE
        # {'uri': None, 'bucket_id': <value>}
        _payload.update(kwargs)
        return _payload

    @classmethod
    def _init_flow_task(cls, task_metadata, payload):
        """Init the flow task metadata."""
        task_metadata.status = FlowTaskStatus.PENDING

        new_payload = dict(task_metadata.payload)
        new_payload.update(payload)

        task_metadata.payload = new_payload
        return task_metadata

    @classmethod
    def create_flow_tasks(cls, payload, task_id=None, **kwargs):
        """Return a list of created Flow Tasks for the current Celery task."""
        if task_id:
            # start only one specific task id
            t = FlowTaskMetadata.get(task_id)
            t = cls._init_flow_task(t, payload)
            return [t]

        flow_tasks_metadata = FlowTaskMetadata.get_all_by_flow_task_name(
            payload["flow_id"], cls.name
        )
        if not flow_tasks_metadata:
            flow_tasks_metadata = [
                FlowTaskMetadata.create(
                    flow_id=payload["flow_id"], name=cls.name
                )
            ]

        ts = []
        for t in flow_tasks_metadata:
            ts.append(cls._init_flow_task(t, payload))

        return ts

    def get_or_create_flow_task(self):
        """Get or create the Flow TaskMetadata for the current flow/task."""
        flow_tasks_metadata = FlowTaskMetadata.get_all_by_flow_task_name(
            self.flow_id, self.name
        )
        if not flow_tasks_metadata:
            flow_task_metadata = FlowTaskMetadata.create(
                self.flow_id, self.name
            )
        else:
            assert len(flow_tasks_metadata) == 1
            flow_task_metadata = flow_tasks_metadata[0]
        return flow_task_metadata


class DownloadTask(AVCTask):
    """Download task."""

    name = "file_download"

    @staticmethod
    def clean(version_id, *args, **kwargs):
        """Undo download task."""
        # Delete the file and the object version
        if version_id:
            dispose_object_version(version_id)

    def run(self, uri, **kwargs):
        """Download file from a URL.

        :param self: reference to instance of task base class
        :param uri: URL of the file to download.
        """
        self._base_payload.update(key=self.object_version.key)

        flow_task_metadata = self.get_or_create_flow_task()
        kwargs["celery_task_id"] = str(self.request.id)
        kwargs["task_id"] = str(flow_task_metadata.id)
        flow_task_metadata.payload = self.get_full_payload(**kwargs)
        flow_task_metadata.status = FlowTaskStatus.STARTED
        flow_task_metadata.message = ""
        db.session.commit()

        self.log("Started task {0}".format(kwargs["task_id"]))

        # Make HTTP request
        response = requests.get(uri, stream=True)

        if "Content-Length" in response.headers:
            headers_size = int(response.headers.get("Content-Length"))
        else:
            headers_size = None

        def progress_updater(size, total):
            """Progress reporter."""
            size = size or headers_size
            if size is None:
                err = 'Cannot locate "Content-Length" header.'
                flow_task_metadata.status = FlowTaskStatus.FAILURE
                flow_task_metadata.message = err
                db.session.commit()
                raise RuntimeError(err)
            # meta = dict(
            #     payload=dict(
            #         size=size,
            #         total=total,
            #         percentage=total * 100 / size,
            #     ),
            #     message="Downloading {0} of {1}".format(total, size),
            # )

        self.object_version.set_contents(
            response.raw, progress_callback=progress_updater, size=headers_size
        )

        db.session.commit()
        self.log("Finished task {0}".format(kwargs["task_id"]))


class ExtractMetadataTask(AVCTask):
    """Extract metadata task."""

    format_keys = [
        "duration",
        "bit_rate",
        "size",
    ]
    stream_keys = [
        "avg_frame_rate",
        "codec_name",
        "codec_long_name",
        "width",
        "height",
        "nb_frames",
        "display_aspect_ratio",
        "color_range",
    ]

    _all_keys = format_keys + stream_keys

    name = "file_video_metadata_extraction"

    def clean(self, deposit_id, version_id, *args, **kwargs):
        """Undo metadata extraction."""
        # 1. Revert patch on record
        pid = PersistentIdentifier.get("depid", deposit_id)
        recid = str(pid.object_uuid)
        patch = [
            {
                "op": "remove",
                "path": "/_cds/extracted_metadata",
            }
        ]
        validator = "cds.modules.records.validators.PartialDraft4Validator"
        try:
            patch_record(recid=recid, patch=patch, validator=validator)
        except jsonpatch.JsonPatchConflict as c:
            logger.warning(
                "Failed to apply JSON Patch to deposit %s: %s", recid, c
            )

        # Delete tmp file if any
        obj = as_object_version(version_id)
        temp_location = obj.get_tags().get("temp_location", None)
        if temp_location:
            shutil.rmtree(temp_location)
            ObjectVersionTag.delete(obj, "temp_location")
            db.session.commit()

    @classmethod
    def get_metadata_from_video_file(cls, object_=None, uri=None):
        """Get metadata from video file."""
        # Extract video's metadata using `ff_probe`
        if uri:
            metadata = ff_probe_all(uri)
        else:
            with move_file_into_local(object_) as url:
                metadata = ff_probe_all(url)
        return dict(metadata["format"], **metadata["streams"][0])

    @classmethod
    def create_metadata_tags(cls, metadata, object_, keys):
        """Create corresponding tags."""
        # Add technical information to the ObjectVersion as Tags
        [
            ObjectVersionTag.create_or_update(object_, k, to_string(v))
            for k, v in metadata.items()
            if k in keys
        ]
        db.session.refresh(object_)
        return metadata

    def run(self, uri=None, *args, **kwargs):
        """Extract metadata from given video file.

        All technical metadata, i.e. bitrate, will be translated into
        ``ObjectVersionTags``, plus all the metadata extracted will be
        store under ``_cds`` as ``extracted_metadata``.

        :param self: reference to instance of task base class
        """
        pid = PersistentIdentifier.get("depid", self.deposit_id)
        recid = str(pid.object_uuid)

        self._base_payload.update(uri=uri)

        flow_task_metadata = self.get_or_create_flow_task()
        kwargs["celery_task_id"] = str(self.request.id)
        kwargs["task_id"] = str(flow_task_metadata.id)
        flow_task_metadata.status = FlowTaskStatus.STARTED
        flow_task_metadata.payload = self.get_full_payload(**kwargs)
        flow_task_metadata.message = ""
        db.session.commit()

        self.log("Started task {0}".format(kwargs["task_id"]))

        metadata = self.get_metadata_from_video_file(
            object_=self.object_version, uri=uri
        )
        try:
            extracted_dict = self.create_metadata_tags(
                metadata, self.object_version, self._all_keys
            )
        except Exception:
            db.session.rollback()
            raise

        tags = self.object_version.get_tags()
        flow_task_metadata.message = "Extracted: " + json.dumps(tags)
        db.session.commit()

        # Insert metadata into deposit's metadata
        patch = [
            {
                "op": "add",
                "path": "/_cds/extracted_metadata",
                "value": extracted_dict,
            }
        ]
        validator = "cds.modules.records.validators.PartialDraft4Validator"
        update_record.s(recid=recid, patch=patch, validator=validator).apply()

        # update Celery task payload with tags
        self._base_payload.update(
            meta=dict(
                payload=dict(
                    tags=tags,
                    extracted_metadata=extracted_dict,
                ),
                message="Attached video metadata",
            )
        )

        self.log("Finished task {0}".format(kwargs["task_id"]))
        return json.dumps(extracted_dict)


class ExtractFramesTask(AVCTask):
    """Extract frames task."""

    name = "file_video_extract_frames"

    @staticmethod
    def clean(version_id, *args, **kwargs):
        """Delete generated ObjectVersion slaves."""
        # remove all objects version "slave" with type "frame" and,
        # automatically, all tags connected
        tag_alias_1 = aliased(ObjectVersionTag)
        tag_alias_2 = aliased(ObjectVersionTag)
        slaves = (
            ObjectVersion.query.join(tag_alias_1, ObjectVersion.tags)
            .join(tag_alias_2, ObjectVersion.tags)
            .filter(
                tag_alias_1.key == "master", tag_alias_1.value == version_id
            )
            .filter(
                tag_alias_2.key == "context_type",
                tag_alias_2.value.in_(["frame", "frames-preview"]),
            )
            .all()
        )
        # FIXME do a test for check separately every "undo" when
        for slave in slaves:
            dispose_object_version(slave)

    def run(
        self, frames_start=5, frames_end=95, frames_gap=10, *args, **kwargs
    ):
        """Extract images from some frames of the video.

        Each of the frame images generates an ``ObjectVersion`` tagged as
        "frame" using ``ObjectVersionTags``.

        :param self: reference to instance of task base class
        :param frames_start: start percentage, default 5.
        :param frames_end: end percentage, default 95.
        :param frames_gap: percentage between frames from start to end,
            default 10.
        """
        # create or update the TaskMetadata db row
        flow_task_metadata = self.get_or_create_flow_task()
        kwargs["celery_task_id"] = str(self.request.id)
        kwargs["task_id"] = str(flow_task_metadata.id)
        flow_task_metadata.payload = self.get_full_payload(**kwargs)
        flow_task_metadata.status = FlowTaskStatus.STARTED
        flow_task_metadata.message = ""
        db.session.commit()

        self.log("Started task {0}".format(kwargs["task_id"]))

        output_folder = tempfile.mkdtemp()

        # Remove temporary directory on abrupt execution halts.
        self.set_revoke_handler(
            lambda: shutil.rmtree(output_folder, ignore_errors=True)
        )

        # Calculate time positions
        options = self._time_position(
            duration=self._base_payload["tags"]["duration"],
            frames_start=frames_start,
            frames_end=frames_end,
            frames_gap=frames_gap,
        )

        def progress_updater(current_frame):
            """Progress reporter."""
            percentage = current_frame / options["number_of_frames"] * 100
            meta = dict(
                payload=dict(size=options["duration"], percentage=percentage),
                message="Extracting frames [{0} out of {1}]".format(
                    current_frame, options["number_of_frames"]
                ),
            )
            self.log(meta["message"])

        bucket_was_locked = False
        if self.object_version.bucket.locked:
            # If record was published we need to unlock the bucket
            bucket_was_locked = True
            self.object_version.bucket.locked = False

        try:
            frames = self._create_frames(
                frames=self._create_tmp_frames(
                    object_=self.object_version,
                    output_dir=output_folder,
                    progress_updater=progress_updater,
                    **options
                ),
                object_=self.object_version,
                **options
            )
        except Exception:
            db.session.rollback()
            shutil.rmtree(output_folder, ignore_errors=True)
            self.clean(version_id=self.object_version_id)
            raise

        # Generate GIF images
        self._create_gif(
            bucket=str(self.object_version.bucket.id),
            frames=frames,
            output_dir=output_folder,
            master_id=self.object_version_id,
        )

        if bucket_was_locked:
            # Lock the bucket again
            self.object_version.bucket.locked = True

        # Cleanup
        shutil.rmtree(output_folder)
        db.session.commit()

        self.log("Finished task {0}".format(kwargs["task_id"]))
        return "Created {0} frames.".format(len(frames))

    @classmethod
    def _time_position(
        cls, duration, frames_start=5, frames_end=95, frames_gap=10
    ):
        """Calculate time positions."""
        duration = float(duration)
        time_step = duration * frames_gap / 100
        start_time = duration * frames_start / 100
        end_time = (duration * frames_end / 100) + 0.01

        number_of_frames = ((frames_end - frames_start) / frames_gap) + 1

        return {
            "duration": duration,
            "start_time": start_time,
            "end_time": end_time,
            "time_step": time_step,
            "number_of_frames": number_of_frames,
        }

    @classmethod
    def _create_tmp_frames(
        cls,
        object_,
        start_time,
        end_time,
        time_step,
        duration,
        output_dir,
        progress_updater=None,
        **kwargs
    ):
        """Create frames in temporary files."""
        # Generate frames
        with move_file_into_local(object_) as url:
            ff_frames(
                input_file=url,
                start=start_time,
                end=end_time,
                step=time_step,
                duration=duration,
                progress_callback=progress_updater,
                output=os.path.join(output_dir, "frame-{:d}.jpg"),
            )
        # sort them
        sorted_ff_frames = sorted(
            os.listdir(output_dir),
            key=lambda f: int(f.rsplit("-", 1)[1].split(".", 1)[0]),
        )
        # return full path
        return [os.path.join(output_dir, path) for path in sorted_ff_frames]

    @classmethod
    def _create_frames(cls, frames, object_, start_time, time_step, **kwargs):
        """Create frames."""

        [
            cls._create_object(
                bucket=object_.bucket,
                key=os.path.basename(filename),
                stream=file_opener_xrootd(filename, "rb"),
                size=os.path.getsize(filename),
                media_type="image",
                context_type="frame",
                master_id=object_.version_id,
                timestamp=start_time + (i + 1) * time_step,
            )
            for i, filename in enumerate(frames)
        ]

        return frames

    @classmethod
    def _create_gif(cls, bucket, frames, output_dir, master_id):
        """Generate a gif image."""
        gif_filename = "frames.gif"
        bucket = as_bucket(bucket)

        images = []
        for f in frames:
            image = Image.open(file_opener_xrootd(f, "rb"))
            # Convert image for better quality
            im = image.convert("RGB").convert(
                "P", palette=Image.ADAPTIVE, colors=255
            )
            images.append(im)
        gif_image = create_gif_from_frames(images)
        gif_fullpath = os.path.join(output_dir, gif_filename)
        gif_image.save(gif_fullpath, save_all=True)
        cls._create_object(
            bucket=bucket,
            key=gif_filename,
            stream=open(gif_fullpath, "rb"),
            size=os.path.getsize(gif_fullpath),
            media_type="image",
            context_type="frames-preview",
            master_id=master_id,
        )

    @classmethod
    def _create_object(
        cls,
        bucket,
        key,
        stream,
        size,
        media_type,
        context_type,
        master_id,
        **tags
    ):
        """Create object versions with given type and tags."""
        obj = ObjectVersion.create(
            bucket=bucket, key=key, stream=stream, size=size
        )
        ObjectVersionTag.create(obj, "master", str(master_id))
        ObjectVersionTag.create(obj, "media_type", media_type)
        ObjectVersionTag.create(obj, "context_type", context_type)
        [ObjectVersionTag.create(obj, k, to_string(tags[k])) for k in tags]


class TranscodeVideoTask(AVCTask):
    """Transcode video task.

    This is CeleryTask is different from the others because there will be
    only one CeleryTask for `n` TaskMetadata db rows (1 per quality)
    """

    name = "file_transcode"

    @classmethod
    def _init_flow_task(cls, task_metadata, payload, quality=None):
        """Init the flow task metadata."""
        task_metadata.status = FlowTaskStatus.PENDING

        # reset payload content
        new_payload = dict()
        new_payload.update(payload)
        new_payload.setdefault("preset_quality", quality)

        task_metadata.payload = new_payload
        return task_metadata

    @classmethod
    def _get_flow_task_by_quality(cls, flow_tasks, quality):
        """Get flow task by checking the preset quality field."""
        flow_task_metadata = [
            task
            for task in flow_tasks
            if task.payload["preset_quality"] == quality
        ]
        return flow_task_metadata[0] if len(flow_task_metadata) == 1 else None

    @classmethod
    def create_flow_tasks(cls, payload, task_id=None, **kwargs):
        """Override default implementation to create Tasks per qualities."""
        if task_id:
            # start only one specific task id
            t = FlowTaskMetadata.get(task_id)
            t = cls._init_flow_task(t, payload)
            return [t]

        ts = FlowTaskMetadata.get_all_by_flow_task_name(
            payload["flow_id"], cls.name
        )

        flow_tasks = []
        # create tasks only for given qualities (or all if None passed)
        wanted_qualities = kwargs.get("qualities", [])
        qs = (
            wanted_qualities
            or current_app.config["CDS_OPENCAST_QUALITIES"].keys()
        )
        for q in qs:
            t = cls._get_flow_task_by_quality(ts, q) if ts else None
            if not t:
                t = FlowTaskMetadata.create(
                    flow_id=payload["flow_id"], name=cls.name
                )
            t = cls._init_flow_task(t, payload, q)
            flow_tasks.append(t)
        return flow_tasks

    def _update_flow_tasks(self, flow_tasks, status, message, **kwargs):
        """Create or update the TaskMetadata status and message."""
        for flow_task_metadata in flow_tasks:
            flow_task_metadata.status = status
            flow_task_metadata.message = message

            quality = flow_task_metadata.payload["preset_quality"]

            new_payload = dict(flow_task_metadata.payload)
            new_payload.update(
                opencast_publication_tag=current_app.config[
                    "CDS_OPENCAST_QUALITIES"
                ][quality]["opencast_publication_tag"],
                **kwargs  # may contain `opencast_event_id`
            )
            # JSONb cols needs to be assigned (not updated) to be persisted
            flow_task_metadata.payload = new_payload

    def on_success(self, *args, **kwargs):
        """Override on success. Transcoding should not set tasks to SUCCESS."""
        # simply reindex the video and project. The status of the tasks will
        # be set by the Celery task that checks the status on OpenCast.
        self._reindex_video_project()

    def clean(self, version_id, *args, **kwargs):
        """Delete generated ObjectVersion slaves."""
        tag_alias_1 = aliased(ObjectVersionTag)
        tag_alias_2 = aliased(ObjectVersionTag)
        slaves = (
            ObjectVersion.query.join(tag_alias_1, ObjectVersion.tags)
            .join(tag_alias_2, ObjectVersion.tags)
            .filter(
                tag_alias_1.key == "master", tag_alias_1.value == version_id
            )
            .filter(
                tag_alias_2.key == "context_type",
                tag_alias_2.value.in_(["subformat"]),
            )
            .all()
        )

        for slave in slaves:
            dispose_object_version(slave)

    def _start_transcodable_flow_tasks_or_cancel(self, wanted_qualities=None):
        """Get transcodable flow tasks or set them to CANCELLED."""
        tags = self.object_version.get_tags()
        # Get master file's width x height
        width = int(tags["width"]) if "width" in tags else None
        height = int(tags["height"]) if "height" in tags else None

        # make sure that requested qualities, if any, are transcodable
        transcodable_qualities = get_qualities(
            video_height=height, video_width=width
        )
        wanted_qualities = wanted_qualities or transcodable_qualities
        # exclude wanted qualities that are not transcodable
        qualities = list(
            set(wanted_qualities).intersection(set(transcodable_qualities))
        )

        # start only PENDING tasks
        ts = FlowTaskMetadata.get_all_by_flow_task_name(
            self.flow_id, self.name
        )
        ts = [t for t in ts if t.status == FlowTaskStatus.PENDING]

        flow_tasks = []
        for t in ts:
            # update payload with Celery task id and base payload
            new_payload = dict(t.payload)
            new_payload.update(
                task_id=str(t.id),
                celery_task_id=str(self.request.id),
                **self._base_payload
            )
            # JSONb cols needs to be assigned (not updated) to be persisted
            t.payload = new_payload

            # cancel not transcodable qualities
            preset_quality = t.payload["preset_quality"]
            if preset_quality not in qualities:
                t.status = FlowTaskStatus.CANCELLED
                t.message = "The quality {0} cannot be transcoded.".format(
                    preset_quality
                )
                self.log(
                    "Cancelling transcoding task {0} for {1}".format(
                        str(t.id), preset_quality
                    )
                )
            else:
                # good, it can be transcoded
                # the status must be PENDING and can be changed to STARTED
                # after the video file has been uploaded to OpenCast and
                # the OpenCast event id is stored in the payload.
                # Otherwise, the STARTED task will be picked by the cron to
                # check the transcoding status on OpenCast.
                t.status = FlowTaskStatus.PENDING
                t.message = "Started transcoding workflow."
                flow_tasks.append(t)
                self.log(
                    "Starting transcoding task {0} for {1}".format(
                        str(t.id), preset_quality
                    )
                )

        db.session.commit()
        return flow_tasks

    def run(self, *args, **kwargs):
        """Launch video transcoding.

        Ensure that only TaskMetadata for transcodable quality
        for every quality.

        :param self: reference to instance of task base class
        """
        wanted_qualities = kwargs.get("qualities", [])
        flow_tasks = self._start_transcodable_flow_tasks_or_cancel(
            wanted_qualities
        )

        self.set_revoke_handler(
            lambda: self._update_flow_tasks(
                flow_tasks=flow_tasks,
                status=FlowTaskStatus.FAILURE,
                message="Abrupt celery stop",
            )
        )

        # launch transcoding workflow in OpenCast
        opencast_event_id = None
        from cds.modules.deposit.api import deposit_video_resolver

        deposit_video = deposit_video_resolver(self.deposit_id)
        try:
            self.log("Starting video upload to OpenCast")
            opencast = OpenCast(deposit_video, self.object_version)
            qualities_to_transcode = [
                t.payload["preset_quality"] for t in flow_tasks
            ]
            opencast_event_id = opencast.run(qualities_to_transcode)

            # store the OpenCast event id in the tags
            ObjectVersionTag.create_or_update(
                self.object_version, "_opencast_event_id", opencast_event_id
            )

            flow_task_status = FlowTaskStatus.STARTED
            flow_task_message = "Video uploaded and OpenCast workflow started."
            self.log(
                flow_task_message
                + " OpenCast event id: {0}".format(opencast_event_id)
            )
        except RequestError as e:
            flow_task_status = FlowTaskStatus.FAILURE
            flow_task_message = (
                "Failed to start Opencast transcoding workflow "
                "for flow with id: {0}. Request failed on: {1}."
                " Error message: {2}"
            ).format(self.flow_id, e.url, e.message)
            self.log(flow_task_message)

        self._update_flow_tasks(
            flow_tasks=flow_tasks,
            status=flow_task_status,
            message=flow_task_message,
            opencast_event_id=opencast_event_id,
        )

        db.session.commit()


def patch_record(recid, patch, validator=None):
    """Patch a record."""
    with db.session.begin_nested():
        record = Record.get_record(recid)
        record = record.patch(patch)
        if validator:
            validator = import_string(validator)
        record.commit(validator=validator)
    return record


@shared_task(bind=True)
def sync_records_with_deposit_files(
    self, deposit_id, max_retries=5, countdown=5
):
    """Low level files synchronize."""
    from cds.modules.deposit.api import deposit_video_resolver

    deposit_video = deposit_video_resolver(deposit_id)
    db.session.refresh(deposit_video.model)
    if deposit_video.is_published():
        try:
            # sync deposit files <--> record files
            deposit_video = deposit_video.edit().publish().commit()
            record_pid, record = deposit_video.fetch_published()
            # save changes
            deposit_video.commit()
            record.commit()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise self.retry(
                max_retries=max_retries, countdown=countdown, exc=exc
            )
        # index the record again
        _, record_video = deposit_video.fetch_published()
        RecordIndexer().index(record_video)


#
# Patch record
#
@shared_task(bind=True)
def update_record(
    self, recid, patch, validator=None, max_retries=5, countdown=5
):
    """Update a given record with a patch.

    Retries ``max_retries`` after ``countdown`` seconds.

    :param recid: the UUID of the record.
    :param patch: the patch operation to apply.
    :param validator: a jsonschema validator.
    :param max_retries: times to retry operation.
    :param countdown: time to sleep between retries.
    """
    if patch:
        try:
            patch_record(recid=recid, patch=patch, validator=validator)
            db.session.commit()
            return recid
        except ConcurrentModificationError as exc:
            db.session.rollback()
            raise self.retry(
                max_retries=max_retries, countdown=countdown, exc=exc
            )


def get_patch_tasks_status(deposit):
    """Get the patch to apply to update record tasks status."""
    old_status = deposit["_cds"]["state"]
    new_status = deposit._current_tasks_status()
    # create tasks status patch
    patches = jsonpatch.make_patch(old_status, new_status).patch
    # make it suitable for the deposit
    for patch in patches:
        patch["path"] = "/_cds/state{0}".format(patch["path"])
    return patches
