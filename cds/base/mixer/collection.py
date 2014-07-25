# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2013 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from six import with_metaclass as meta

from invenio.ext.mixer import MixerMeta
from invenio.modules.search.models import Collection, CollectionCollection, \
    CollectionExample, CollectionExternalcollection, \
    CollectionFieldFieldvalue, CollectionFormat, CollectionPortalbox, \
    Collectionboxname, Collectiondetailedrecordpagetabs, Collectionname, \
    Externalcollection, Portalbox


class ExternalcollectionMixer(meta(MixerMeta)):
    __model__ = Externalcollection


class CollectiondetailedrecordpagetabsMixer(meta(MixerMeta)):
    __model__ = Collectiondetailedrecordpagetabs


class CollectionMixer(meta(MixerMeta)):
    __model__ = Collection
    __fields__ = ('id', 'name', 'dbquery')


class CollectionCollectionMixer(meta(MixerMeta)):
    __model__ = CollectionCollection


class CollectionFieldFieldvalueMixer(meta(MixerMeta)):
    __model__ = CollectionFieldFieldvalue


class CollectionFormatMixer(meta(MixerMeta)):
    __model__ = CollectionFormat


class PortalboxMixer(meta(MixerMeta)):
    __model__ = Portalbox


class CollectionnameMixer(meta(MixerMeta)):
    __model__ = Collectionname


class CollectionboxnameMixer(meta(MixerMeta)):
    __model__ = Collectionboxname


__all__ = ('ExternalcollectionMixer', 'CollectiondetailedrecordpagetabsMixer',
           'CollectionMixer', 'CollectionCollectionMixer',
           'CollectionFormatMixer', 'CollectionFieldFieldvalueMixer',
           'PortalboxMixer', 'CollectionnameMixer', 'CollectionboxnameMixer', )
