# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016-2026 CERN.
#
# CERN Document Server is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Image of CDS Videos for docker-compose.full.yml. The Invenio base image
# provides Python 3.14, Node.js 24, pnpm, uv, the invenio user and the instance
# layout (/opt/invenio/src with its .venv, /opt/invenio/var/instance), as for
# zenodo-rdm. The OpenShift image is built by cds-videos-openshift.
#
# Build: docker build -f docker/app/Dockerfile -t cds-videos .

ARG BUILD_PLATFORM=linux/amd64
FROM --platform=${BUILD_PLATFORM} ghcr.io/inveniosoftware/invenio:debian-python3.14

# python-ldap has no wheel and is built against OpenLDAP
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        libldap2-dev \
        libsasl2-dev && \
    rm -rf /var/lib/apt/lists/*

# FFmpeg 5.0 (static build)
RUN mkdir /usr/local/bin/ffmpeg && \
    curl -fsSL https://cds-resources.web.cern.ch/cds-resources/cds-videos/ffmpeg/5.0/ffmpeg-release-amd64-static.tar.xz | \
        tar -xJ --strip-components=1 --directory=/usr/local/bin/ffmpeg/ && \
    ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg && \
    ln -s /usr/local/bin/ffmpeg/ffprobe /usr/bin/ffprobe

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    INVENIO_COLLECT_STORAGE=flask_collect.storage.file

# Python dependencies of uv.lock in /opt/invenio/src/.venv, in their own layer
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --extra xrootd --no-install-project

# Application, then uWSGI next to it (not part of uv.lock)
COPY . .
RUN uv sync --locked --no-dev --extra xrootd && \
    uv pip install "uWSGI==2.0.31" "uwsgi-tools==1.1.1" "uwsgitop==0.11"

# Static files and assets: the JavaScript packages come from pnpm-lock.yaml
# and the build fails if the generated package.json differs from the committed
# one (see scripts/build-assets)
RUN ./scripts/build-assets && \
    rm -rf ${INVENIO_INSTANCE_PATH}/assets

# OpenShift runs with an arbitrary UID in GID 0
RUN chown -R invenio:0 ${WORKING_DIR} && \
    chmod -R g=u ${WORKING_DIR}

USER invenio

EXPOSE 5000

ENTRYPOINT ["bash", "-c"]
