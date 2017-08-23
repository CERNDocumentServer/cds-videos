#!/bin/sh

# quit on errors:
set -o errexit

# quit on unbound symbols:
set -o nounset

# ElasticSearch
ES_VERSION=$1
mkdir /tmp/elasticsearch
wget -O - https://download.elasticsearch.org/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/${ES_VERSION}/elasticsearch-${ES_VERSION}.tar.gz | tar xz --directory=/tmp/elasticsearch --strip-components=1
/tmp/elasticsearch/bin/plugin install mapper-attachments -b
/tmp/elasticsearch/bin/elasticsearch &

# FFMpeg
mkdir /tmp/ffmpeg
# FIXME could we remove the --no-check-certificate?
wget -O - https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-64bit-static.tar.xz --no-check-certificate | tar --strip-components 1 -xJ -C /tmp/ffmpeg && export PATH=$PATH:/tmp/ffmpeg

# Pip
pip install --upgrade pip setuptools py
pip install twine wheel coveralls requirements-builder
