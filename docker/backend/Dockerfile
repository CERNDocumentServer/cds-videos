#
# Copyright (C) 2018-2020 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
ARG CENTOS_VERSION=7
FROM centos:${CENTOS_VERSION} AS docker-invenio

RUN yum install -y \
        yum-utils \
        curl \
        git \
        rlwrap \
        screen \
        vim \
        emacs-nox && \
    yum install -y \
        epel-release && \
    yum groupinstall -y "Development Tools" && \
    yum install -y \
        cairo-devel \
        dejavu-sans-fonts \
        libffi-devel \
        libxml2-devel \
        libxslt-devel \
        ImageMagick

RUN yum clean -y all

# install nodejs version 8
RUN curl -sL https://rpm.nodesource.com/setup_8.x | bash - && \
    yum install -y nodejs

# install and set python3.6 as default
RUN yum install -y centos-release-scl && \
    yum install -y rh-python36
RUN echo '#!/bin/bash' >> /etc/profile.d/enablepython36.sh && \
    echo '. scl_source enable rh-python36' >> /etc/profile.d/enablepython36.sh
ENV BASH_ENV=/etc/profile.d/enablepython36.sh

RUN chmod -R g=u /etc/profile.d/enablepython36.sh /opt/rh/rh-python36 && \
    chgrp -R 0 /etc/profile.d/enablepython36.sh /opt/rh/rh-python36
SHELL ["/bin/bash", "-c"]

# setuptools v58 removed 2to3 support: https://setuptools.pypa.io/en/latest/history.html#v58-0-0
# the `fs` package relies on `2to3`
RUN pip --version && pip install --upgrade pip pipenv "setuptools==44.1.1" wheel

# set the locale
RUN localedef --quiet -c -i en_US -f UTF-8 en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Create working directory
ENV WORKING_DIR=/opt/invenio
ENV INVENIO_INSTANCE_PATH=${WORKING_DIR}/var/instance
RUN mkdir -p ${INVENIO_INSTANCE_PATH}

# Create files mountpoints
RUN mkdir ${INVENIO_INSTANCE_PATH}/data
RUN mkdir ${INVENIO_INSTANCE_PATH}/archive
RUN mkdir ${INVENIO_INSTANCE_PATH}/static

# copy everything inside /src
RUN mkdir -p ${WORKING_DIR}/src
WORKDIR ${WORKING_DIR}/src

# Set `npm` global under Invenio instance path
RUN mkdir ${INVENIO_INSTANCE_PATH}/.npm-global
ENV NPM_CONFIG_PREFIX=$INVENIO_INSTANCE_PATH/.npm-global
RUN mkdir npm_install && cd npm_install && \
    curl -SsL https://registry.npmjs.org/npm/-/npm-6.14.5.tgz | tar -xzf - && \
    cd package && \
    node bin/npm-cli.js rm npm -g && \
    node bin/npm-cli.js install -g $(node bin/npm-cli.js pack | tail -1) && \
    cd ../.. && rm -rf npm_install

RUN npm config set prefix '${INVENIO_INSTANCE_PATH}/.npm-global'
ENV PATH=${INVENIO_INSTANCE_PATH}/.npm-global/bin:$PATH

# Set folder permissions
ENV INVENIO_USER_ID=1000
RUN chgrp -R 0 ${WORKING_DIR} && \
    chmod -R g=u ${WORKING_DIR}
RUN useradd invenio --uid ${INVENIO_USER_ID} --gid 0 && \
    chown -R invenio:root ${WORKING_DIR}


###########################################
# Tempfix of docker invenio
FROM docker-invenio
########################################################################################
# XRootD and dependencies
ENV INVENIO_XROOTD_VERSION=4.12.2
# needed because older version of xrootd, e.g. 4.12.2, are only available there
RUN yum-config-manager --add-repo https://xrootd.slac.stanford.edu/binaries/xrootd-stable-slc7.repo
RUN yum --setopt=obsoletes=0 install -y \
    cmake gcc-c++ zlib-devel openssl-devel libuuid-devel python3-devel \
    xrootd-${INVENIO_XROOTD_VERSION} \
    xrootd-client-${INVENIO_XROOTD_VERSION} \
    xrootd-client-devel-${INVENIO_XROOTD_VERSION} \
    xrootd-python-${INVENIO_XROOTD_VERSION}

########################################################################################
# OpenLDAP
RUN yum install -y openldap-devel

########################################################################################

RUN yum clean -y all

# We invalidate cache always because there is no easy way for now to detect
# if something in the whole git repo changed. For docker git clone <url> <dir>
# is always the same so it caches it.
ARG CACHE_DATE=not_a_date
RUN echo "Cache date: $CACHE_DATE"

ENV BACKEND_WORKING_DIR=${WORKING_DIR}/src/backend

# get the code at a specific commit
RUN mkdir -p ${BACKEND_WORKING_DIR}
RUN git clone https://github.com/zzacharo/cds-videos.git ${BACKEND_WORKING_DIR}
WORKDIR ${BACKEND_WORKING_DIR}

# check if one of the argument is passed to checkout the repo on a specific commit, otherwise use the latest
ARG BRANCH_NAME
ARG COMMIT_ID
ARG TAG_NAME
ARG PR_ID
RUN if [ ! -z $BRANCH_NAME ]; then \
        # run commands to checkout a branch
        echo "Checkout branch $BRANCH_NAME" && \
        git checkout $BRANCH_NAME; \
    elif [ ! -z $COMMIT_ID ]; then \
        # run commands to checkout a commit
        echo "Checkout commit $COMMIT_ID" && \
        git checkout $COMMIT_ID; \
    elif [ ! -z $TAG_NAME ]; then \
        # run commands to checkout a tag
        echo "Checkout tag $TAG_NAME" && \
        git checkout tags/$TAG_NAME; \
    elif [ ! -z $PR_ID ]; then \
        # run commands to checkout a pr
        echo "Checkout PR #$PR_ID" && \
        git fetch origin pull/$PR_ID/head:$PR_ID && \
        git checkout $PR_ID; \
    fi

# print current commit id
RUN echo "Current commit id:" && git rev-parse HEAD

ENV INVENIO_STATIC_FOLDER=${INVENIO_INSTANCE_PATH}/static

# Installs all packages specified in Pip requirements file
ARG INVENIO_PIP_REQUIREMENTS_FILE
RUN pip install "pip>=20,<21"
RUN echo "Installing requirements from file $INVENIO_PIP_REQUIREMENTS_FILE" && \
    pip install -r $INVENIO_PIP_REQUIREMENTS_FILE
RUN echo "Installing Python xrootd==${INVENIO_XROOTD_VERSION}" && \
    pip install xrootd==${INVENIO_XROOTD_VERSION} invenio-xrootd==1.0.0a6
RUN pip install -e .
RUN pip freeze

RUN npm config set user 0
RUN npm install -g node-sass@3.8.0 clean-css@3.4.24 uglify-js requirejs

USER 1000

RUN cds npm
WORKDIR ${INVENIO_STATIC_FOLDER}
RUN npm install
WORKDIR ${BACKEND_WORKING_DIR}}
RUN cds collect -v && \
    cds assets build && \
    cds webpack buildall

ENTRYPOINT [ "bash", "-c"]
