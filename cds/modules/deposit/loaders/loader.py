# -*- coding: utf-8 -*-
#
# This file is part of CERN Document Server.
# Copyright (C) 2016 CERN.
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

"""Marshmallow loaders."""

from __future__ import absolute_import

import json

from flask import request, has_request_context, current_app
from invenio_rest.errors import RESTValidationError


def _doi_context():
    """Configure DOI Context."""
    # Replace refs when we are in request context.
    context = dict(replace_refs=has_request_context())

    # DOI validation context
    if request and request.view_args and request.view_args.get('pid_value'):
        managed_prefix = current_app.config['PIDSTORE_DATACITE_DOI_PREFIX']

        _, record = request.view_args.get('pid_value').data
        #  context['recid'] = record['recid']
        if record.has_minted_doi():
            context['required_doi'] = record['doi']
        #  elif not record.is_published():
        #      context['allowed_dois'] = [doi_generator(record['recid'])]
        elif record.is_published():
            # Ensure we cannot change to e.g. empty string.
            context['doi_required'] = True

        context['managed_prefixes'] = [managed_prefix]
        context['banned_prefixes'] = \
            ['10.5072'] if managed_prefix != '10.5072' else []

    return context


def marshmallow_loader(schema_class, partial=False):
    """Marshmallow loader."""
    def schema_loader():
        request_json = request.get_json()

        context = _doi_context()

        result = schema_class(context=context,
                              partial=partial).load(request_json)
        if result.errors:
            raise MarshmallowErrors(result.errors)
        return result.data
    return schema_loader


class MarshmallowErrors(RESTValidationError):
    """Marshmallow validation errors."""

    def __init__(self, errors):
        """Store marshmallow errors."""
        self.errors = errors
        super(MarshmallowErrors, self).__init__()

    def __str__(self):
        """Print exception with errors."""
        return "{base}. Encountered errors: {errors}".format(
            base=super(RESTValidationError, self).__str__(),
            errors=self.errors)

    def iter_errors(self, errors, prefix=''):
        """Iterator over marshmallow errors."""
        res = []
        for field, error in errors.items():
            if isinstance(error, list):
                res.append(dict(
                    field='{0}{1}'.format(prefix, field),
                    message=' '.join([str(x) for x in error])
                ))
            elif isinstance(error, dict):
                res.extend(self.iter_errors(
                    error,
                    prefix='{0}{1}.'.format(prefix, field)
                ))
        return res

    def get_body(self, environ=None):
        """Get the request body."""
        body = dict(
            status=self.code,
            message=self.get_description(environ),
        )

        if self.errors:
            body['errors'] = self.iter_errors(self.errors)

        return json.dumps(body)
