# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
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

from collections import OrderedDict, namedtuple
from functools import partial
import pprint
import urlparse
import warnings
from dojson.contrib.marc21.utils import split_blob, create_record


class SplitWarning(Warning):
    pass


class SplitException(Exception):
    pass


class RecordSplitter(object):
    _main_type = None
    _new_type = None
    _copy_fields_list = []
    id_offset = 0

    @staticmethod
    def _force_list(data):  # it is implemented in doJson, should I use function from it? or implement it here?
        if data is not None and not isinstance(data, (list, set)):
            return [data]
        return data

    @staticmethod
    def _reverse_force_list(data):
        if len(data) == 1:
            return data[0]
        return data

    def split_records_string(self, batch_string):
        """Splits the marcxml string to json-like structure

        If batch_string contains several records it returns
        the list of tuples (main_record, list_of_new_records)
        else it returns tuple (main_records, list_of_new_records)

        :param batch: marcxml string of records
        :return: tuple or list of tuples
        """
        assert isinstance(batch_string, basestring)
        records = [create_record(data) for data in split_blob(batch_string)]
        return self.split_records(self._reverse_force_list(records))

    def split_records(self, records):
        """Splits the container-record to separate records

        If records contains several records it returns
        the list of tuples (main_record, list_of_new_records)
        else it returns tuple (main_records, list_of_new_records)

        :param records: dict  or list containing records to split
        :return: list of lists of splitted records
        """
        assert isinstance(records, (dict, list))
        if isinstance(records, list):
            return map(self._transform_record, records)
        return self._transform_record(records)

    def _transform_record(self, record):
        assert isinstance(record, dict)

        new_records_base = self._get_new_record_base(record)
        photo_records = [self._new_record_factory(*record_base)
                         for record_base in enumerate(new_records_base)]

        self._set_references(record, photo_records)
        self._copy_fields(record, photo_records)
        self._set_records_types(record, photo_records)
        return (record, photo_records)

    def _set_records_types(self, main_records, new_records):
        """Sets main_type for the main_records and new_type for new_records"""
        set_type = lambda record, typ: record.__setitem__('999__', {'a': typ})

        map(partial(set_type, typ=self.__class__._main_type),
            self.__class__._force_list(main_records))
        map(partial(set_type, typ=self.__class__._new_type),
            self.__class__._force_list(new_records))

    def _new_record_factory(self, index, *args):
        return {
            '001': [str(index + self.__class__.id_offset)]
        }

    def _set_references(self, main_record, new_records):
        main_recid = main_record['001'][0]
        main_type = self.__class__._main_type
        new_type = self.__class__._new_type

        [rec.__setitem__('774__', {'a': main_type, 'r': main_recid}) for rec in new_records]
        [main_record.__setitem__('774__', {'a': new_type, 'r': rec['001'][0]}) for rec in new_records]

    def _copy_fields(self, main_record, new_records):
        for field in self.__class__._copy_fields_list:
            if field in main_record:
                copy_function = getattr(self, '_copy_%s' % field,
                                        partial(self._copy_default, field=field))
                for new_record in new_records:
                    copy_function(main_record, new_record)

    def _copy_default(self, main_record, new_record, field):
        new_record[field] = main_record[field]


class AlbumSplitter(RecordSplitter):
    _main_type = 'ALBUM'
    _new_type = 'IMAGE'
    id_offset = 5000000
    _copy_fields_list = [
        '037__',
        '100__',
        '245__',
        '260__',
        '269__',
        '540__',
        '542__',
        '700__',
    ]

    @staticmethod
    def pop_new_record_fields(record):
        unique_key_fun = lambda media_field: urlparse.urlsplit(media_field.get('u')).path.rsplit('/', 1)[-1]
        media_result = namedtuple('MediaResult', ['field', 'filename'])

        # remove icons
        record['8564_'] = [field for field in AlbumSplitter._force_list(record['8564_']) if not field.get('x') or not field.get('x').startswith('icon')]

        photos = [media_result(media, unique_key_fun(media))
                  for media in AlbumSplitter._force_list(record['8564_'])
                  if media.get('u')]

        for photo in photos:
            record['8564_'].remove(photo.field)

        if record['8564_']:
            raise SplitException(str(record['8564_']))
        #     warnings.warn("Album %s have uncovered cases of 8564 field" % str(record['001'][0]), SplitWarning)

        return photos

    def _get_new_record_base(self, record):
        new_record_base = OrderedDict()
        media_fields_tuples = self.__class__.pop_new_record_fields(record)
        for media_field, unique_key in media_fields_tuples:
            if unique_key not in new_record_base:
                new_record_base[unique_key] = []
            new_record_base[unique_key].append(media_field)
        return new_record_base.values()

    def _new_record_factory(self, index, field, *args):
        record = super(AlbumSplitter, self)._new_record_factory(index)
        record['8564_'] = field
        return record

    def _transform_record(self, record):
        record, photo_records = super(AlbumSplitter, self)._transform_record(record)
        for photo in photo_records:
            photo['8564_'] = self._reverse_force_list(photo['8564_'])

        return record, photo_records

    def _copy_037__(self, main_record, new_record):
        common_field = main_record['037__']['a']
        counter = new_record.get('8564_')[0].get('c', '')
        new_record['037__'] = {
            'a': common_field + counter
        }


def test():
    # filepath = '/home/theer/Documents/CERN/split2.xml'
    filepath = '/home/theer/Documents/CERN/split-one-8564.xml'
    # filepath = '/home/theer/Documents/CERN/.xml'
    with open(filepath, 'r') as fd:
        a = AlbumSplitter()
        return a.split_records_string(fd.read())


def test_batch():
    filepath = '/home/theer/Documents/CERN/photos_to_split.xml'
    with open(filepath, 'r') as fd:
        splitter = AlbumSplitter()
        records = [create_record(data) for data in split_blob(fd.read())]
        counter = 0
        for album in records:
            try:
                result = splitter.split_records(album)
                counter += 1
                if counter % 1000 == 0:
                    print '%s/%s' % (counter, len(records))
            except SplitException, e:
                print ('='*15 + 'Album: %s' + '='*15) % album['001'][0]
                pprint.pprint(e.args)
                print '=' * 35
            except Exception, e:
                print ('!'*15 + 'Album: %s' + '!'*15) % album['001'][0]
                pprint.pprint(e.args)
                print '!' * 35
