# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""JS/CSS bundles for CDS Previewer."""

from __future__ import absolute_import, print_function

from flask_assets import Bundle
from invenio_assets import NpmBundle

theoplayer_js = Bundle(
    # ui-sortable requires jquery to be already loaded
    'js/cds_previewer/theoplayer/theoplayer.loader.js',
    filters='jsmin',
    output='gen/cds.previewer.oplayer.%(version)s.js',
)

video_css = Bundle(
    'css/cds_previewer/video.css',
    filters='cleancssurl',
    output='gen/cds.previewer.%(version)s.css',
)

theoplayer_css = Bundle(
    'css/cds_previewer/theoplayer/theoplayer.css',
    filters='cleancssurl',
    output='gen/cds.previewer.oplayer.%(version)s.css',
)
