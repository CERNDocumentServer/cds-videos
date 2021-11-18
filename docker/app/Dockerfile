# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2020 CERN.
#
# invenio-app-ils is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

FROM python:3.6

RUN apt-get update && apt-get upgrade -y && apt-get install apt-file -y && apt-file update
RUN cd /tmp && curl -sL https://deb.nodesource.com/setup_12.x -o nodesource_setup.sh && bash nodesource_setup.sh

RUN apt-get install -y nodejs git curl vim ffmpeg
RUN pip install --upgrade "setuptools<58" wheel pip uwsgi uwsgitop uwsgi-tools

RUN python -m site
RUN python -m site --user-site

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

# needed to build node-gyp, required from node-sass, as root
RUN npm config set user 0
RUN ./scripts/bootstrap

# Set folder permissions
RUN chgrp -R 0 ${WORKING_DIR} && \
    chmod -R g=u ${WORKING_DIR}

RUN useradd invenio --uid 1000 --gid 0 && \
    chown -R invenio:root ${WORKING_DIR}
USER 1000

ENTRYPOINT ["bash", "-c"]
