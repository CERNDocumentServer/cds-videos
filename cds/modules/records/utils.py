# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017, 2018, 2019 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Helper methods for CDS records."""

from __future__ import absolute_import, print_function

import json

import six
from elasticsearch.exceptions import NotFoundError
from flask import current_app, g, request
from flask_security import current_user
from invenio_db import db
from invenio_files_rest.models import as_bucket
from invenio_files_rest.tasks import remove_file_data
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.errors import PersistentIdentifierError
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.providers.datacite import DataCiteProvider
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from invenio_records_files.models import RecordsBuckets
from invenio_search import current_search
from invenio_search.utils import schema_to_index
from six.moves.html_parser import HTMLParser
from six.moves.urllib.parse import urlparse
from sqlalchemy_continuum import version_class

from ..deposit.fetcher import deposit_fetcher
from .fetchers import recid_fetcher


def schema_prefix(schema):
    """Get index prefix for a given schema."""
    if not schema:
        return None
    index, doctype = schema_to_index(
        schema, index_names=current_search.mappings.keys()
    )
    return index.split("-")[0]


def is_record(record):
    """Determine if a record is a bibliographic record."""
    return schema_prefix(record.get("$schema")) == "records"


def is_deposit(record):
    """Determine if a record is a deposit record."""
    return schema_prefix(record.get("$schema")) == "deposits"


def is_project_record(record):
    project_schema = current_jsonschemas.url_to_path(record["$schema"])
    return "records/videos/project/project-v" in project_schema


def lowercase_value(value):
    """Lowercase value if not an integer.

    This function is used when we compare user's identity groups and record's
    stored `_access` values. If the value is not a string, it is considered the
    user ID (integer) and thus we return it unchanged.
    """
    lowercase_value = ""
    try:
        lowercase_value = value.lower()
    except AttributeError:
        # Add the user ID (integer) to the list
        lowercase_value = value
    return lowercase_value


def get_user_provides():
    """Extract the user's provides from g."""
    return [lowercase_value(need.value) for need in g.identity.provides]


def remove_html_tags(html_tag_remover, value):
    """Remove any HTML tags."""
    html_tag_remover.reset()
    html_tag_remover.feed(value)
    return html_tag_remover.get_data()


def format_pid_link(url_template, pid_value):
    """Format a pid url."""
    if request:
        return url_template.format(
            host=request.host, scheme=request.scheme, pid_value=pid_value
        )
    else:
        r = urlparse(current_app.config["THEME_SITEURL"])
        return url_template.format(
            host=r.netloc, scheme=r.scheme, pid_value=pid_value
        )


class HTMLTagRemover(HTMLParser):
    """Remove all HTML tags by keeping only the value within the tag."""

    values = []

    def reset(self):
        """Reset the list of values."""
        HTMLParser.reset(self)
        self.values = []

    def handle_data(self, data):
        """Append only the value within the tags."""
        self.values.append(data)

    def get_data(self):
        """Return only values."""
        return "".join(self.values)


def _get_record_and_deposit(record_uuid):
    """Find a record and it's deposit from the record UUID."""
    from ..deposit.api import Project, Video
    from ..deposit.api import is_project_record as is_project_deposit

    record = Record.get_record(record_uuid)
    deposit = None

    if is_record(record):
        deposit_cls = Project if is_project_record(record) else Video
        try:
            depid = deposit_fetcher(None, record)
            _, deposit = Resolver(
                pid_type=depid.pid_type,
                object_type="rec",
                getter=deposit_cls.get_record,
            ).resolve(depid.pid_value)
        except (PersistentIdentifierError, AttributeError):
            # there is no deposit associated with the record
            pass
    else:
        deposit_cls = Project if is_project_deposit(record) else Video
        deposit = deposit_cls(record, model=record.model)
        try:
            record = deposit.fetch_published()
        except (PersistentIdentifierError, KeyError):
            record = None

    return record, deposit


def delete_project_record(record_uuid, reason=None, hard=False):
    """Delete project."""
    from ..deposit.api import Video

    report = []
    _, deposit = _get_record_and_deposit(record_uuid)

    if deposit:
        videos = deposit.videos
        # Delete each video first
        for video in videos:
            report.append(("INFO", "Removing Video {}".format(video.id)))
            if "pid" in video["_deposit"]:
                # Find published video
                record_pid = recid_fetcher(None, video)
                video_pid, deposit = Resolver(
                    pid_type=record_pid.pid_type,
                    object_type="rec",
                    getter=Record.get_record,
                ).resolve(record_pid.pid_value)
            else:
                # Find deposit
                depid = deposit_fetcher(None, video)
                video_pid, deposit = Resolver(
                    pid_type=depid.pid_type,
                    object_type="rec",
                    getter=Video.get_record,
                ).resolve(depid.pid_value)
            report.extend(
                delete_video_record(video_pid.object_uuid, reason, hard)
            )
        # Save all changes made so far
        db.session.commit()

    if hard:
        report.extend(wipe_record(record_uuid))
    else:
        report.extend(delete_record(record_uuid, reason=reason))

    # Save all changes made so far
    db.session.commit()

    return report


def delete_video_record(record_uuid, reason=None, hard=False):
    """Delete video."""
    from invenio_indexer.api import RecordIndexer

    report = []
    _, deposit = _get_record_and_deposit(record_uuid)
    if deposit:
        # Start deleting the deposit
        if hard:
            deposit._delete_flows()
            report.append(
                (
                    "INFO",
                    "Deleted all flows for deposit {}.".format(
                        deposit.id
                    ),
                )
            )

        project = deposit.project
        project_uuid = project.id
        if project.is_published():
            try:
                project = project.edit()
                project._delete_videos([deposit.ref])
                project.publish().commit()
                report.append(
                    (
                        "INFO",
                        "Removed Video {0} from project {1}.".format(
                            deposit.id, project.id
                        ),
                    )
                )
            except Exception as e:
                report.append(
                    (
                        "WARN",
                        "Couldn't remove Video from project. {}".format(e),
                    )
                )
        else:
            try:
                project._delete_videos([deposit.ref])
                project.commit()
                report.append(
                    (
                        "INFO",
                        "Removed Video {0} from project {1}.".format(
                            deposit.id, project.id
                        ),
                    )
                )
            except Exception as e:
                report.append(
                    (
                        "WARN",
                        "Couldn't remove Video from project. {}".format(e),
                    )
                )
        # Save all changes made so far
        db.session.commit()
        # Reindex the project to delete the video reference
        report.append(("INFO", "Reindexing project."))
        RecordIndexer().index_by_id(project_uuid)

    if hard:
        report.extend(wipe_record(record_uuid))
    else:
        report.extend(delete_record(record_uuid, reason))

    return report


def _delete_doi(record):
    """Mark DOI as deleted."""
    if not "doi" in record:
        return
    try:
        doi = PersistentIdentifier.get("doi", record["doi"])
        dcp = DataCiteProvider.get(doi.pid_value)
        dcp.delete()
        return ("INFO", "DOI deleted for record {}".format(doi))
    except Exception as e:
        return (
            "WARN",
            "Couldn't delete DOI from record {0} - {1}".format(record.id, e),
        )


def wipe_record(record_uuid):
    """Delete completely a record from the system."""
    from invenio_indexer.api import RecordIndexer

    report = [("INFO", "Wiping record {}".format(record_uuid))]
    file_ids = []

    for record in _get_record_and_deposit(record_uuid):
        if record is None:
            continue
        uuid = record.id

        # Remove the record from index
        try:
            RecordIndexer().delete(record)
            report.append(("INFO", "Deleted record from index."))
        except NotFoundError:
            report.append(("WARN", "Couldn't delete record from index."))

        # Delete PIDs
        try:
            PersistentIdentifier.query.filter(
                PersistentIdentifier.object_uuid == uuid,
                PersistentIdentifier.pid_type != "doi",
            ).delete()
            report.append(("INFO", "Deleted PIDs from record."))
        except Exception as e:
            report.append(
                ("ERROR", "Couldn't delete PIDs from record - {}.".format(e))
            )

        report.append(_delete_doi(record))

        # Delete record bucket reference
        record_bucket = RecordsBuckets.query.filter(
            RecordsBuckets.record_id == uuid
        ).one_or_none()
        try:
            RecordsBuckets.query.filter(
                RecordsBuckets.record_id == uuid
            ).delete()
            report.append(("INFO", "Deleted RecordBucket from record."))
        except Exception as e:
            report.append(
                (
                    "ERROR",
                    "Couldn't delete RecordBucket from record - {}.".format(e),
                )
            )

        # Delete metadata and versions
        try:
            RecordMetadataVersion = version_class(RecordMetadata)
            db.session.query(RecordMetadataVersion).filter(
                RecordMetadataVersion.id == uuid
            ).delete()
            RecordMetadata.query.filter(RecordMetadata.id == uuid).delete()
            report.append(("INFO", "Deleted record metadata and versions."))
        except Exception as e:
            report.append(
                ("ERROR", "Couldn't delete record metadata - {}.".format(e))
            )

        # Delete Files
        file_ids = []
        if record_bucket:
            bucket = as_bucket(record_bucket.bucket_id)
            record_bucket.bucket.locked = False
            # Make files writable
            for obj in bucket.objects:
                # skip if file is None (due to a previous soft deletion)
                if not obj.file:
                    continue
                file_ids.append(str(obj.file.id))
                obj.file.writable = True
                db.session.add(obj.file)
            try:
                bucket.remove()
                report.append(("INFO", "Deleted bucket."))
            except Exception as e:
                report.append(
                    ("ERROR", "Couldn't delete bucket- {}.".format(e))
                )

    db.session.commit()

    # Completely delete files
    for file_id in file_ids:
        try:
            task = remove_file_data.delay(file_id)
            report.append(
                (
                    "INFO",
                    "File {0} deleted from disk by task {1}.".format(
                        uuid, task.id
                    ),
                )
            )
        except Exception as e:
            report.append(
                ("ERROR", "Couldn't delete file from disk - {}.".format(e))
            )

    return report


def delete_record(record_uuid, reason):
    """Delete record and store the deleting reason within the JSON."""
    from invenio_indexer.api import RecordIndexer

    report = [
        ("INFO", "Deleting record {0} - {1}".format(record_uuid, reason))
    ]
    for record in _get_record_and_deposit(record_uuid):
        if record is None:
            continue
        uuid = record.id

        # Mark all pid as deleted
        for pid in PersistentIdentifier.query.filter(
            PersistentIdentifier.object_uuid == uuid,
            PersistentIdentifier.pid_type != "doi",
        ):
            try:
                pid.delete()
            except Exception as e:
                report.append(("ERROR", "Couldn't delete PID {}".format(e)))

        report.append(_delete_doi(record))

        # Remove the record from index
        try:
            RecordIndexer().delete(record)
            report.append(("INFO", "Deleted record from index."))
        except NotFoundError:
            report.append(("WARN", "Couldn't delete record from index."))

        record_bucket = RecordsBuckets.query.filter(
            RecordsBuckets.record_id == uuid
        ).one_or_none()
        try:
            RecordsBuckets.query.filter(
                RecordsBuckets.record_id == uuid
            ).delete()
            report.append(("INFO", "Deleted RecordBucket from record."))
        except Exception as e:
            report.append(
                (
                    "ERROR",
                    "Couldn't delete RecordBucket from record - {}.".format(e),
                )
            )
        if record_bucket:
            bucket = as_bucket(record_bucket.bucket_id)
            bucket.locked = False
            try:
                bucket.remove()
                report.append(("INFO", "Deleted bucket."))
            except Exception as e:
                report.append(
                    ("ERROR", "Couldn't delete bucket- {}.".format(e))
                )

        if is_record(record):
            # Clear the record and put the deletion information
            removal_reasons = dict(current_app.config["CDS_REMOVAL_REASONS"])
            if reason in removal_reasons:
                reason = removal_reasons[reason]
            try:
                record.clear()
                record.update(
                    {
                        "removal_reason": reason,
                        "removed_by": int(current_user.get_id()),
                    }
                )
                record.commit()
                report.append(
                    ("INFO", "Update record content with {}".format(reason))
                )
            except Exception as e:
                report.append(
                    ("ERROR", "Couldn't update record content {}".format(e))
                )
        else:
            # Completely delete the deposit
            try:
                record.model.json = None
                db.session.merge(record.model)
                report.append(("INFO", "Delete deposit content."))
            except Exception as e:
                report.append(
                    ("ERROR", "Couldn't delete deposit content {}".format(e))
                )

    db.session.commit()

    return report


def to_string(value):
    """Ensure that the input value is returned as a string."""
    if isinstance(value, six.string_types):
        return value
    else:
        return json.dumps(value)
