# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Deposit loaders."""

from cds.modules.deposit.loaders.loader import marshmallow_loader
from cds.modules.records.serializers.schemas.project import ProjectSchema
from cds.modules.records.serializers.schemas.video import VideoSchema

# Loaders for project schema.
project_loader = marshmallow_loader(ProjectSchema)
partial_project_loader = marshmallow_loader(ProjectSchema, partial=True)

# Loaders for video schema.
video_loader = marshmallow_loader(VideoSchema)
partial_video_loader = marshmallow_loader(VideoSchema, partial=True)
