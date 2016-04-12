# -*- coding: utf-8 -*-
#
# This file is part of CDS.
#
# Copyright (C) 2015 CERN.
#
# CDS is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
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

pydocstyle --match-dir='[^\.|(cds\/modules\/record_split)].*' cds && \
isort -rc -c -df **/*.py && \
check-manifest --ignore ".travis-*" && \
py.test tests/unit/
