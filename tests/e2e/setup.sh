#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# This file is part of CDS.
# Copyright (C) 2026 CERN.
#
# CDS is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.

# An instance for the end to end tests, on empty services: the database, the
# indices, the users and fixtures of scripts/setup (without the keywords
# harvested from home.cern) and the records of seed.py.

set -o errexit
set -o nounset

script_path=$(dirname "$0")

cds db init create
cds index init --force
cds index queue init purge
cds queues declare

cds users create test@test.ch -a --password=123456
cds users create admin@test.ch -a --password=123456
cds roles create admin
cds roles create cern-user
cds roles add test@test.ch cern-user
cds roles add admin@test.ch admin
cds access allow deposit-admin-access role admin
cds access allow superuser-access role admin
cds access allow videos-upload-access role cern-user

mkdir -p "${E2E_FILES_PATH:-/tmp/files}"
cds files location --default videos "${E2E_FILES_PATH:-/tmp/files}"

cds fixtures sequence-generator
cds fixtures categories
cds fixtures pages
cds fixtures licenses
cds index reindex -t od_lic --yes-i-know
cds index run

python "$script_path"/seed.py
