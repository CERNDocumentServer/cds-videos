# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
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
# 59 Temple Place, Suite 330, Boston, MA 02D111-1307, USA.

"""Generic record spliter"""

from collections import OrderedDict, Sequence

from functools import partial

from dojson import utils

from dojson.contrib.marc21.utils import create_record, split_blob

from six import with_metaclass


class RecordSplitterMeta(type):
    """Metaclass for RecordSplitter"""

    def __new__(metacls, name, bases, dct):
        """__new__"""

        result = super(RecordSplitterMeta,
                       metacls
                       ).__new__(metacls, name, bases, dct)
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


class RecordSplitter(with_metaclass(RecordSplitterMeta, object)):
    """RecordSplitter class definition"""

    _main_record_type = None
    _new_record_type = None
    _copy_fields_list = []

    def __init__(self):
        self._next_id = 5000000

    def get_next_id(self):
        self._next_id += 1
        return self._next_id - 1  # TODO: max(recid) from DB

    def split(self, records):
        """Splits the container-record to separate records

        If records contains several records it returns
        the list of tuples (main_record, list_of_new_records)
        else it returns tuple (main_records, list_of_new_records)

        :param records: dict  or list containing records to split
        :return: list of lists of splitted records
        """
        if isinstance(records, basestring):
            records = [create_record(data) for data in split_blob(records)]
        elif isinstance(records, dict):
            records = [records]
        return map(self._transform_record, records)

    def _get_new_records_base(self, record):
        result = []
        for field_filter in self._filters:
            result.extend(field_filter(record=record))
        return result

    def _transform_record(self, record):
        assert isinstance(record, dict)

        new_records_base = self._get_new_records_base(record)
        new_records = [self._new_record_factory(record_base)
                       for record_base in new_records_base]

        self._set_references(record, new_records)
        self._copy_fields(record, new_records)
        self._set_records_types(record, new_records)
        self._remove_fields(record)

        return record, new_records

    def _set_records_types(self, main_records, new_records):
        """Sets main_type for the main_records and new_type for new_records"""
        def set_type(record, typ):
            record.__setitem__(u'999__', {'a': typ})

        map(partial(set_type, typ=self.__class__._main_record_type),
            _force_list(main_records))
        map(partial(set_type, typ=self.__class__._new_record_type),
            _force_list(new_records))

    def _new_record_factory(self, field):
        key, value = field.items()[0]
        record = {
            u'001': [str(self.get_next_id())],
            key: value
        }
        return record

    def _set_references(self, main_record, new_records):
        if not main_record or not new_records:
            return
        type_tag = u'774__'
        main_recid = main_record['001'][0]
        main_type = self.__class__._main_record_type
        new_type = self.__class__._new_record_type

        assert not main_record.get(type_tag) \
            or isinstance(main_record[type_tag], Sequence)
        main_record[type_tag] = _force_list(main_record.get(type_tag))

        for record in new_records:
            assert not record.get(type_tag) \
                or isinstance(record[type_tag], Sequence)
            record[type_tag] = _force_list(record.get(type_tag))

        [rec[type_tag].append({'a': main_type, 'r': main_recid})
            for rec in new_records]
        [main_record[type_tag].append({'a': new_type, 'r': rec['001'][0]})
            for rec in new_records]

        main_record[type_tag] = _reverse_force_list(main_record[type_tag])
        for record in new_records:
            record[type_tag] = _reverse_force_list(record[type_tag])

    def _copy_fields(self, main_record, new_records):
        for field in self.__class__._copy_fields_list:
            if field in main_record:
                copy_function = getattr(self,
                                        'copy_%s' % field,
                                        partial(self.copy_default,
                                                field=field))
                for new_record in new_records:
                    copy_function(main_record, new_record)

    def _remove_fields(self, main_record):
        for remover in self._removers:
            remover(record=main_record)

    def copy_default(self, main_record, new_record, field):
        new_record[field] = main_record[field]

    @staticmethod
    def common_filter(record, field_tag, predicate, unique_key_fun):
        record[field_tag] = _force_list(record[field_tag])
        if not record[field_tag]:
            return []
        new_record_base = OrderedDict()
        for field in record[field_tag]:
            if predicate(field):
                unique_key = unique_key_fun(field)
                if not new_record_base.get(unique_key):
                    new_record_base[unique_key] = []
                new_record_base[unique_key].append(field)
        return [{field_tag: l} for l in new_record_base.values()]

    @staticmethod
    def common_remove(record, field_tag, new_value):
        if new_value:
            record[field_tag] = new_value
        else:
            del record[field_tag]


def _reverse_force_list(data):
    if len(data) == 1:
        return data[0]
    return data


def _force_list(data):
    if data is None:
        return []
    return utils.force_list(data)
