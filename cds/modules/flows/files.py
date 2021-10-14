from __future__ import absolute_import
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record
from sqlalchemy.orm.attributes import flag_modified
from invenio_files_rest.models import (
    ObjectVersion,
    ObjectVersionTag,
    as_object_version,
)

from contextlib import contextmanager
import tempfile
import shutil
import os

from invenio_db import db


from ..xrootd.utils import file_opener_xrootd


def _update_flow_bucket(flow):
    """Update event's payload with correct bucket of deposit."""
    from cds.modules.deposit.api import deposit_video_resolver
    deposit_bucket = deposit_video_resolver(
        flow.payload['deposit_id']
    ).files.bucket
    flow.payload['bucket_id'] = str(deposit_bucket.id)
    flag_modified(flow.model, 'payload')
    db.session.commit()


def init_object_version(flow):
    """Create, if doesn't exists, the version object for the flow."""
    flow_id = str(flow.id)
    with db.session.begin_nested():
        # create a object version if doesn't exists
        if flow.payload.get('version_id'):
            version_id = flow.payload['version_id']
            object_version = as_object_version(version_id)
        else:
            object_version = ObjectVersion.create(
                bucket=flow.payload['bucket_id'], key=flow.payload['key']
            )
            ObjectVersionTag.create(
                object_version, 'uri_origin', flow.payload['uri']
            )
            version_id = str(object_version.version_id)
            flow.payload['version_id'] = version_id
        # add tag with corresponding event
        ObjectVersionTag.create_or_update(
            object_version, '_flow_id', flow_id
        )
        # add tag for preview
        ObjectVersionTag.create_or_update(object_version, 'preview', 'true')
        # add tags for file type
        ObjectVersionTag.create_or_update(
            object_version, 'media_type', 'video'
        )
        ObjectVersionTag.create_or_update(
            object_version, 'context_type', 'master'
        )
        flag_modified(flow.model, 'payload')
    return object_version


def dispose_object_version(object_version):
    """Clean up resources related to an ObjectVersion."""
    if object_version:
        object_version = as_object_version(object_version)
        # remove the object version
        ObjectVersion.delete(
            bucket=object_version.bucket, key=object_version.key)


@contextmanager
def move_file_into_local(obj, delete=True):
    """Move file from XRootD accessed file system into a local path

    :param obj: Object version to make locally available.
    :param delete: Whether or not the tmp file should be deleted on exit.
    """
    if os.path.exists(obj.file.uri):
        yield obj.file.uri
    else:
        temp_location = obj.get_tags().get('temp_location', None)
        if not temp_location:
            temp_folder = tempfile.mkdtemp()
            temp_location = os.path.join(temp_folder, 'data')

            with open(temp_location, 'wb') as dst:
                shutil.copyfileobj(file_opener_xrootd(obj.file.uri, 'rb'), dst)

            ObjectVersionTag.create(obj, 'temp_location', temp_location)
            db.session.commit()
        else:
            temp_folder = os.path.dirname(temp_location)
        try:
            yield temp_location
        except:
            shutil.rmtree(temp_folder)
            ObjectVersionTag.delete(obj, 'temp_location')
            db.session.commit()
            raise
        else:
            if delete:
                shutil.rmtree(temp_folder)
                ObjectVersionTag.delete(obj, 'temp_location')
                db.session.commit()
