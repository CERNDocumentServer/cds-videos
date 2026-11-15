# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2026 CERN.
#
# CDS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# CDS is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CDS; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""IIIF handlers of the frames and posters.

Invenio-IIIF 1.2.0 (unmaintained) imports ``pkg_resources`` in its handlers
module, which setuptools 82 removed. The configuration points Flask-IIIF to
these copies instead (``IIIF_API_DECORATOR_HANDLER`` and
``IIIF_IMAGE_OPENER_HANDLER``).
"""

import tempfile

from flask import g
from invenio_files_rest.views import ObjectResource


def protect_api(uuid=None, **kwargs):
    """Get the object of the image and check the read permission.

    :param uuid: The image key, as ``<bucket>:<version>:<key>``.
    """
    bucket, version_id, key = uuid.split(":", 2)
    g.obj = ObjectResource.get_object(bucket, key, version_id)
    return g.obj


def image_opener(key):
    """Open the file of an image.

    The first page of PDF and text files is converted to PNG when Wand
    (ImageMagick) is available, as in Invenio-IIIF.

    :param key: The image key, as ``<bucket>:<version>:<key>``.
    :returns: A file-like object.
    """
    obj = g.obj if hasattr(g, "obj") else protect_api(key)
    fp = obj.file.storage().open("rb")
    if obj.mimetype in ("application/pdf", "text/plain"):
        try:
            from wand.image import Image
        except ImportError:
            return fp
        first_page = Image(Image(fp).sequence[0])
        converted_fp = tempfile.TemporaryFile()
        with first_page.convert(format="png") as converted:
            converted.save(file=converted_fp)
        return converted_fp
    return fp
