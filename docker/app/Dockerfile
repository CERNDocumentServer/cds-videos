# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2020 CERN.
#
# invenio-app-ils is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

FROM registry.cern.ch/inveniosoftware/almalinux:1

RUN dnf install -y epel-release
RUN dnf update -y

RUN cd /tmp && curl -sL  https://rpm.nodesource.com/setup_16.x  -o nodesource_setup.sh && bash nodesource_setup.sh
RUN dnf install -y nodejs git vim

# OpenLDAP
RUN dnf install -y openldap-devel

# FFMPEG
RUN yum install -y wget
RUN mkdir /usr/local/bin/ffmpeg && \
    wget -O - https://cds-resources.web.cern.ch/cds-resources/cds-videos/ffmpeg/5.0/ffmpeg-release-amd64-static.tar.xz | tar -xJ --strip-components=1 --directory=/usr/local/bin/ffmpeg/ && \
    ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg && \
    ln -s /usr/local/bin/ffmpeg/ffprobe /usr/bin/ffprobe

RUN yum clean -y all

RUN pip install "uWSGI==2.0.23" "uwsgi-tools==1.1.1" "uwsgitop==0.11"

# Install Invenio
ENV WORKING_DIR=/opt/cds_videos
ENV VIRTUAL_ENV=${WORKING_DIR}
ENV INVENIO_INSTANCE_PATH=${WORKING_DIR}/var/instance
ENV INVENIO_STATIC_FOLDER=${INVENIO_INSTANCE_PATH}/static

# copy everything inside /src
RUN mkdir -p ${WORKING_DIR}/src
COPY ./ ${WORKING_DIR}/src
WORKDIR ${WORKING_DIR}/src

# Install/create static files
RUN mkdir -p ${INVENIO_INSTANCE_PATH}
RUN mkdir -p ${INVENIO_STATIC_FOLDER}

# Create files folder
RUN mkdir -p ${INVENIO_INSTANCE_PATH}/files


RUN ./scripts/bootstrap

# Set folder permissions
RUN chgrp -R 0 ${WORKING_DIR} && \
    chmod -R g=u ${WORKING_DIR}

RUN useradd invenio --uid 1000 --gid 0 && \
    chown -R invenio:root ${WORKING_DIR}
USER 1000

ENTRYPOINT ["bash", "-c"]
