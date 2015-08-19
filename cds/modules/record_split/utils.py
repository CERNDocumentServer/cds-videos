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
import traceback
import urlparse
import warnings
from six import with_metaclass
from dojson.contrib.marc21.utils import split_blob, create_record


class SplitWarning(Warning):
    pass


class SplitException(Exception):
    pass


class Double037Field(SplitException):
    pass


class RecordSplitterMetaclass(type):
    def __new__(metacls, name, bases, dct):
        result = super(RecordSplitterMetaclass, metacls).__new__(metacls, name, bases, dct)
        result._filters = []
        result._copiers = []
        result._removers = []
        for key, value in dct.iteritems():
            if key.startswith('filter'):
                result._filters.append(partial(value, self=result))
            elif key.startswith('copy'):
                result._copiers.append(partial(value, self=result))
            elif key.startswith('remove'):
                result._removers.append(partial(value, self=result))
        return result

class RecordSplitter(with_metaclass(RecordSplitterMetaclass, object)):
    _main_type = None
    _new_type = None
    _copy_fields_list = []
    id_offset = 0

    @staticmethod
    def _force_list(data):  # it is implemented in doJson, should I use function from it? or implement it here?
        if data is None:
            return []
        if not isinstance(data, (list, set)):
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

    def _get_new_records_base(self, record):
        result = []
        # try:
        for field_filter in self._filters:
            result.extend(field_filter(record=record))
        return result
        # except Exception, e:
        #     message = "Exception filtering fields. Album: %s, exception: %s" % (record['001'][0], str(e))
        #     warnings.warn(message)
        #     raise SplitException(message)

    def _transform_record(self, record):
        assert isinstance(record, dict)

        new_records_base = self._get_new_records_base(record)
        # new_records_base = self._get_new_record_base(record)
        photo_records = [self._new_record_factory(*record_base)
                         for record_base in enumerate(new_records_base)]

        self._set_references(record, photo_records)
        self._copy_fields(record, photo_records)
        self._set_records_types(record, photo_records)
        self._remove_fields(record)

        self.assertions(record, photo_records)
        return record, photo_records

    def assertions(self, record, photo_records):
        pass

    def _set_records_types(self, main_records, new_records):
        """Sets main_type for the main_records and new_type for new_records"""
        set_type = lambda record, typ: record.__setitem__('999__', {'a': typ})

        map(partial(set_type, typ=self.__class__._main_type),
            self.__class__._force_list(main_records))
        map(partial(set_type, typ=self.__class__._new_type),
            self.__class__._force_list(new_records))

    def _new_record_factory(self, index, field, *args):
        key, value = field.items()[0]
        record = {
            '001': [str(index + self.__class__.id_offset)],
            key: value
        }
        return record

    def _set_references(self, main_record, new_records):
        main_recid = main_record['001'][0]
        main_type = self.__class__._main_type
        new_type = self.__class__._new_type

        [rec.__setitem__('774__', {'a': main_type, 'r': main_recid}) for rec in new_records]
        [main_record.__setitem__('774__', {'a': new_type, 'r': rec['001'][0]}) for rec in new_records]

    def _copy_fields(self, main_record, new_records):
        for field in self.__class__._copy_fields_list:
            if field in main_record:
                copy_function = getattr(self, 'copy_%s' % field,
                                        partial(self.copy_default, field=field))
                for new_record in new_records:
                    copy_function(main_record, new_record)

    def _remove_fields(self, main_record):
        # try:
        for remover in self._removers:
            remover(record=main_record)
        # except Exception, e:
        #     message = "Exception removing fields. Album: %s, exception: %s" % (main_record['001'][0], str(e))
        #     warnings.warn(message)
        #     raise SplitException(message)

    def copy_default(self, main_record, new_record, field):
        new_record[field] = main_record[field]

    @staticmethod
    def common_filter(record, field_tag, predicate, unique_key_fun):
        # unique_key_fun = lambda media_field: urlparse.urlsplit(media_field.get('u')).path.rsplit('/', 1)[-1]
        record[field_tag] = AlbumSplitter._force_list(record[field_tag])
        new_record_base = OrderedDict()
        for field in record[field_tag]:
            if predicate(field):
                unique_key = unique_key_fun(field)
                if not new_record_base.get(unique_key):
                    new_record_base[unique_key] = []
                new_record_base[unique_key].append(field)
        return [{field_tag: l} for l in new_record_base.values()]


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

    q_allowed_hostnames = ['http://doc.cern.ch', 'http://cds.cern.ch', 'http://cdsweb.cern.ch']
    q_banned_hostnames = ['http://preprints.cern.ch', 'http://documents.cern.ch']

    @classmethod
    def allowed_hostname(cls, url):
        return urlparse.urlsplit(url).hostname.lower() in cls.q_allowed_hostnames

    @classmethod
    def predicate(cls, field):
        return (
            (
                not field.get('x')
                or
                not field.get('x').startswith('icon')
            )
            and
            (
                field.get('u')
                or
                (
                    field.get('q')
                    and
                    cls.allowed_hostname(field.get('q'))
                )
            )
        )

    def filter_8564_(self, record):
        unique_key_fun = lambda media_field: urlparse.urlsplit(media_field.get('u') or media_field.get('q')).path.rsplit('/', 1)[-1]
        return RecordSplitter.common_filter(record, '8564_', self.predicate, unique_key_fun)

    def filter_8567_(self, record):
        unique_key_fun = lambda media_field: media_field.get('8')
        predigate_fun = lambda field: field.get('2') == 'MediaArchive'
        return RecordSplitter.common_filter(record, '8567_', predigate_fun, unique_key_fun)

    def remove_8564_(self, record):
        is_known_hostname_fun = partial(lambda x, known:
                                        len([False for y in known if x.startswith(y)]) != 0, known=self.q_allowed_hostnames+self.q_banned_hostnames)

        if record.get('8564_'):
            q_list = [is_known_hostname_fun(elm.get('q')) for elm in record['8564_'] if elm.get('q')]
            if q_list:
                assert all(q_list), record['8564_']  # all hostnames are aknowledged

        cleared_field = []
        for field in AlbumSplitter._force_list(record['8564_']):
            if field.get('x'):
                if field['x'].startswith('icon'):
                    continue
            if not self.predicate(field):
                cleared_field.append(field)

        record['8564_'] = cleared_field

    def remove_8567_(self, record):
        record['8567_'] = [field for field in AlbumSplitter._force_list(record['8567_']) if field.get('2') != 'MediaArchive']

    def copy_037__(self, main_record, new_record):
        if not isinstance(main_record['037__'], dict):
            raise Double037Field
        common_field = main_record['037__']['a']
        counter = None

        if new_record.get('8564_'):
            counter = new_record.get('8564_')[0].get('c', '')
        elif new_record.get('8567_'):
            counter = new_record.get('8567_')[0].get('8', '')

        if not counter:
            warnings.warn("Counter isn't specified")

        new_record['037__'] = {
            'a': common_field + counter
        }

    def _transform_record(self, record):
        record, photo_records = super(AlbumSplitter, self)._transform_record(record)
        for photo in photo_records:
            if photo.get('8564_'):
                photo['8564_'] = self._reverse_force_list(photo['8564_'])
            if photo.get('8567_'):
                photo['8567_'] = self._reverse_force_list(photo['8567_'])

        return record, photo_records













def test():
    # filepath = '/home/theer/Documents/CERN/split2.xml'
    filepath = '/home/theer/Documents/CERN/split-one-8564.xml'
    # filepath = '/home/theer/Documents/CERN/.xml'
    with open(filepath, 'r') as fd:
        a = AlbumSplitter()
        return a.split_records_string(fd.read())


def test_batch():
    filepath = '/home/theer/Documents/CERN/photos_to_split.xml'
    # filepath = '/home/theer/Documents/CERN/split/tiny-photos-to-split.xml'
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
            except Double037Field, e:
                print '=============== Double 037 field: %s' % album['001'][0]
            except SplitException, e:
                print ('='*15 + 'Album: %s' + '='*15) % album['001'][0]
                pprint.pprint(e.args)
                print '=' * 35
            except Exception, e:
                print ('!'*15 + 'Album: %s' + '!'*15) % album['001'][0]
                traceback.print_exc()
                pprint.pprint(e.args)
                print '!' * 35
