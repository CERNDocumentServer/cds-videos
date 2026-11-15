# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Validators."""


from jsonschema.validators import Draft4Validator, extend

DRAFT4_SCHEMAS = {
    Draft4Validator.META_SCHEMA["id"],
    Draft4Validator.META_SCHEMA["id"].rstrip("#"),
}


def no_validation(v, r, i, s):
    """Dummy method to omit jsonschema validation."""
    return None


def _same_dialect(schema):
    """Drop the draft 4 ``$schema`` of a referenced schema.

    Since jsonschema 4.10 a validator following a ``$ref`` switches to the
    class of the ``$schema`` declared by the referenced schema. For the CDS
    schemas that is the full ``Draft4Validator``, which checks what the
    partial validator skips. Without ``$schema`` the class is kept.
    """
    if isinstance(schema, dict) and schema.get("$schema") in DRAFT4_SCHEMAS:
        return {key: value for key, value in schema.items() if key != "$schema"}
    return schema


def ref_same_dialect(validator, ref, instance, schema):
    """Validate a ``$ref`` with the class of the current validator."""
    if validator._ref_resolver is None:
        resolved = validator._resolver.lookup(ref)
        yield from validator.descend(
            instance, _same_dialect(resolved.contents), resolver=resolved.resolver
        )
    else:
        scope, resolved = validator._ref_resolver.resolve(ref)
        validator._ref_resolver.push_scope(scope)
        try:
            yield from list(validator.descend(instance, _same_dialect(resolved)))
        finally:
            validator._ref_resolver.pop_scope()


PartialDraft4Validator = extend(
    Draft4Validator,
    validators={
        "$ref": ref_same_dialect,
        "required": no_validation,
        "minItems": no_validation,
        "maxItems": no_validation,
        "uniqueItems": no_validation,
    },
)
