# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

###############################################################################
## 1. Base (stable)                                                          ##
###############################################################################

# TODO: Change to the Invenio version as soon as PR#147 is accepted.
FROM cdslabs/invenio-base

ENV INVENIO_MODULE="cds"
WORKDIR /src/$INVENIO_MODULE

# OPTIONAL Install vim or other packeges - uncomment to use
# RUN apt-get update && \
#     apt-get -qy install --fix-missing --no-install-recommends \
#         vim \
#         && \
#     apt-get clean autoclean && \
#     apt-get autoremove -y && \
#     rm -rf /var/lib/{apt,dpkg}/ && \
#     (find /usr/share/doc -depth -type f ! -name copyright -delete || true) && \
#     (find /usr/share/doc -empty -delete || true) && \
#     rm -rf /usr/share/man/* /usr/share/groff/* /usr/share/info/*

# Allow sudo
RUN echo "alias ll='ls -alF'" >>  /home/invenio/.bashrc && \
    echo "invenio ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

###############################################################################
## 2. Requirements (semi-stable)                                             ##
###############################################################################

COPY ./$INVENIO_MODULE/version.py /src/$INVENIO_MODULE/$INVENIO_MODULE/

# Dev - Test requierments first (for caching)
COPY ./dev.requirements.txt \
     ./test.requirements.txt \
     /src/$INVENIO_MODULE/

RUN cd / && \
    pip install -r /src/$INVENIO_MODULE/dev.requirements.txt --exists-action i --upgrade && \
    rm -rf /tmp/* /var/tmp/* /var/lib/{cache,log}/ /root/.cache/*

###############################################################################
## 3. Build (changing)                                                       ##
###############################################################################

# Choose if invenio is build from cdslabs or cdslabs_qa
ENV CDSLABS="cdslabs"
# ENV CDSLABS="cdslabs_qa"

# Base and setup.py requirements
COPY ./requirements.txt \
     ./requirements.$CDSLABS.txt \
     ./base.requirements.txt \
     ./base-pinned.requirements.txt \
     ./setup.py \
     /src/$INVENIO_MODULE/

# Change the BUILD variable to trigger a new build of the remote repository's.
ENV BUILD=1

# sed -i '/CERNDocumentServer\/invenio/d' requirements.txt
# install python requirements, remove invenio from requirements
RUN sed -i "s/-e \./-e \/src\/$INVENIO_MODULE\/\./g" requirements.$CDSLABS.txt && \
    cd / && \
    pip install -r /src/$INVENIO_MODULE/requirements.$CDSLABS.txt --exists-action i --upgrade && \
    rm -rf /tmp/* /var/tmp/* /var/lib/{cache,log}/ /root/.cache/*


###############################################################################
## 3. Code (changing)                                                        ##
###############################################################################

# add current directory as `/code`.
COPY . /src/$INVENIO_MODULE

# in general code should not be writable, especially because we are using
# `pip install -e`
RUN mkdir -p /src/$INVENIO_MODULE && \
    chown -R invenio:invenio /src/$INVENIO_MODULE


###############################################################################
## 3. Bower install (changing)                                               ##
###############################################################################

# Temporary config and Bower install.
# Config needed for the upfront Bower installation.

RUN cfgfile=$INVENIOBASE_INSTANCE_PATH/invenio.cfg && \

    # TODO: Check why file needs to exist
    mkdir -p /usr/local/var/log && \
    touch /usr/local/var/log/invenio_base.log && \
    chown invenio /usr/local/var/log/invenio_base.log && \

    echo "CFG_BATCHUPLOADER_DAEMON_DIR = u'/opt/invenio/var/batchupload'" >> $cfgfile && \
    echo "CFG_BIBSCHED_LOGDIR = u'/opt/invenio/var/log/bibsched'" >> $cfgfile && \
    echo "CFG_BIBEDIT_CACHEDIR = u'/opt/invenio/var/tmp-shared/bibedit-cache'" >> $cfgfile && \
    echo "CFG_BIBSCHED_LOGDIR = u'/opt/invenio/var/log/bibsched'" >> $cfgfile && \
    echo "CFG_BINDIR = u'/usr/local/bin'" >> $cfgfile && \
    echo "CFG_CACHEDIR = u'/opt/invenio/var/cache'" >> $cfgfile && \
    echo "CFG_ETCDIR = u'/opt/invenio/etc'" >> $cfgfile && \
    echo "CFG_LOCALEDIR = u'/opt/invenio/share/locale'" >> $cfgfile && \
    echo "CFG_LOGDIR = u'/opt/invenio/var/log'" >> $cfgfile && \
    echo "CFG_PYLIBDIR = u'/usr/local/lib/python2.7'" >> $cfgfile && \
    echo "CFG_RUNDIR = u'/opt/invenio/var/run'" >> $cfgfile && \
    echo "CFG_TMPDIR = u'/tmp/invenio-`hostname`'" >> $cfgfile && \
    echo "CFG_TMPSHAREDDIR = u'/opt/invenio/var/tmp-shared'" >> $cfgfile && \
    echo "CFG_WEBDIR = u'/opt/invenio/var/www'" >> $cfgfile && \
    echo "CFG_BIBDOCFILE_FILEDIR = u'/opt/invenio/var/data/files'" >> $cfgfile && \
    cd /src/$INVENIO_MODULE


USER invenio

RUN inveniomanage bower -o bower.json && \
    mkdir -p $INVENIOBASE_STATIC_FOLDER/vendors && \
    ln -s $INVENIOBASE_STATIC_FOLDER/vendors bower_components && \
    rm .bowerrc && \
    bower install -q -f && \
    inveniomanage collect && \
    rm -f $cfgfile

###############################################################################
## 5. Final Steps (changing)                                                 ##
###############################################################################

# FIXME: Why needs to be manually installed?
RUN sudo pip install datacite

VOLUME ["/src/$INVENIO_MODULE"]
