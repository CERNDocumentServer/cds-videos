# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2012, 2013, 2014 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from __future__ import absolute_import, print_function

from wtforms import validators
from werkzeug.local import LocalProxy
from invenio.base.i18n import _, language_list_long
from datetime import date
from invenio.modules.deposit.types import SimpleRecordDeposition
from invenio.modules.deposit.form import WebDepositForm
from invenio.modules.deposit import fields
from invenio.modules.deposit.filter_utils import strip_string, sanitize_html
from invenio.modules.deposit.field_widgets import date_widget, \
    ExtendedListWidget, CKEditorWidget, ColumnInput, ItemWidget
from invenio.modules.deposit.validation_utils import required_if, \
    list_length


def keywords_autocomplete(form, field, term, limit=50):
    return [{'value': "Keyword 1"}, {'value': "Keyword 2"}]


#
# Helpers
#
def filter_empty_helper(keys=None):
    """ Remove empty elements from a list"""
    def _inner(elem):
        if isinstance(elem, dict):
            for k, v in elem.items():
                if (keys is None or k in keys) and v:
                    return True
            return False
        else:
            return bool(elem)
    return _inner


#
# Forms
#
class AuthorInlineForm(WebDepositForm):
    """
    Author inline form
    """
    name = fields.TextField(
        placeholder=_("Family name, First name"),
        validators=[
            required_if(
                'affiliation',
                [lambda x: bool(x.strip()), ],  # non-empty
                message=_("Creator name is required if you specify affiliation.")
            ),
        ],
        widget=ColumnInput(class_="col-xs-6"),
        widget_classes='form-control',
    )
    affiliation = fields.TextField(
        placeholder=_("Affiliation"),
        widget_classes='form-control',
        widget=ColumnInput(class_="col-xs-4 col-pad-0"),
    )


class TalkForm(WebDepositForm):
    #
    # Fields
    #
    category = fields.SelectField(
        choices=[('Talk', 'Talk'), ('Lecture', 'Lecture')],
        default='Talk',
        export_key='collections.secondary',
        widget_classes='form-control',
    )

    title = fields.TextField(
        description=_('Please do not use only UPPER Case'),
        export_key='title.title',
        icon='fa fa-book fa-fw',
        label=_('Title'),
        validators=[validators.Required()],
        widget_classes="form-control",
    )

    authors = fields.DynamicFieldList(
        fields.FormField(
            AuthorInlineForm,
            widget=ExtendedListWidget(
                item_widget=ItemWidget(),
                html_tag='div',
            ),
        ),
        add_label=_('Add another author'),
        export_key='authors',
        icon='fa fa-user fa-fw',
        label=_('Authors'),
        min_entries=1,
        validators=[validators.Required(), list_length(
            min_num=1, element_filter=filter_empty_helper(),
        )],
        widget_classes='',
    )

    abstract = fields.TextAreaField(
        default='',
        export_key='abstract.summary',
        filters=[
            sanitize_html(),
            strip_string,
        ],
        icon='fa fa-pencil fa-fw',
        label=_("Abstract"),
        widget=CKEditorWidget(
            toolbar=[
                ['PasteText', 'PasteFromWord'],
                ['Bold', 'Italic', 'Strike', '-',
                    'Subscript', 'Superscript', ],
                ['NumberedList', 'BulletedList'],
                ['Undo', 'Redo', '-', 'Find', 'Replace', '-', 'RemoveFormat'],
                ['SpecialChar', 'ScientificChar'], ['Source'], ['Maximize'],
            ],
            disableNativeSpellChecker=False,
            extraPlugins='scientificchar',
            removePlugins='elementspath',
        ),
    )

    keywords = fields.DynamicFieldList(
        fields.TextField(
            widget_classes='form-control',
            autocomplete=keywords_autocomplete,
            widget=ColumnInput(class_="col-xs-10"),
        ),
        add_label=_('Add another keyword'),
        icon='fa fa-tags fa-fw',
        label=_('Keywords'),
        min_entries=1,
        widget_classes='',
    )

    comments = fields.TextAreaField(
        description=_('Optional.'),
        default='',
        export_key='comment',
        filters=[
            strip_string,
        ],
        icon='fa fa-pencil fa-fw',
        label=_("Comments or Notes"),
        validators=[validators.optional()],
        widget_classes='form-control',
    )

    release_date = fields.Date(
        default=date.today(),
        description=_('Required. Format: YYYY-MM-DD.'),
        export_key='imprint.date',
        icon='fa fa-calendar fa-fw',
        label=_('Release date'),
        validators=[validators.required()],
        widget=date_widget,
        widget_classes='input-sm',
    )

    pages = fields.TextField(
        export_key='physical_description.pagination',
        icon='fa fa-file-text fa-fw',
        label=_("Pages"),
        validators=[validators.required()],
        widget_classes='form-control',
    )

    language = fields.SelectField(
        choices=LocalProxy(lambda: language_list_long(
            enabled_langs_only=False)),
        default='english',
        export_key='language',
        icon='fa fa-globe fa-fw',
        validators=[validators.required()],
        widget_classes='form-control',
    )

    contact = fields.TextField(
        export_key='address.email',
        icon='fa fa-at fa-fw',
        label=_("Contact (author) email address"),
        validators=[validators.required()],
        widget_classes='form-control',
    )

    # TODO: No idea where to put the next 3 fields
    conference_name = fields.TextField(
        label=_("Conference name"),
        widget_classes='form-control',
    )

    conference_town = fields.TextField(
        description=_('Do not specify a country. * means no town specified'),
        icon='fa fa-globe fa-fw',
        label=_("Conference town"),
        widget_classes='form-control',
    )

    conference_date = fields.Date(
        description=_('Required. Format: YYYY-MM-DD.'),
        default=date.today(),
        icon='fa fa-calendar fa-fw',
        label=_('Conference starting date'),
        # TODO: configure datepicker to allow only YYYY-MM
        widget=date_widget,
        widget_classes='input-sm',
    )

    report_number = fields.TextField(
        default='',
        export_key='relationship.report_number',
        description=_('If this TALK is related to a Conference Proceeding \
                       that exists in CDS, please enter here the related \
                       report number so that the two documents can be linked'),
        filters=[
            strip_string,
        ],
        icon='fa fa-book fa-fw',
        label=_("Report Number"),
        validators=[validators.optional()],
        widget_classes='form-control',
    )

    additional_url = fields.TextField(
        default='',
        description=_('Only if the conference is not in CDS'),
        export_key='publication_info.url',
        filters=[
            strip_string,
        ],
        label=_("Additional Conference URL"),
        validators=[validators.optional()],
        widget_classes='form-control',
    )

    #
    # Form configuration
    #
    _title = _('New talk')
    _subtitle = _('Instructions: (i) Press "Save" to save your upload for '
                  'editing later, as many times you like. (ii) When ready, '
                  'press "Submit" to finalize your upload.')

    groups = [
        ('Basic Information',
            ['category', 'title', 'authors'],
            {
                'indication': 'required',
            }),
        ('Description',
            ['abstract', 'keywords', 'comments', ],
            {
                'indication': 'optional',
            }),
        ('Additional Information',
            ['release_date', 'pages', 'language', 'contact',
             'journal_pages'],
            {
                'indication': 'required'
            }),
        ('Conference Information',
            ['conference_name', 'conference_town', 'conference_date'],
            {
                'indication': 'optional',
            }),
        ('Related Documents',
            ['report_number', 'additional_url'],
            {
                'indication': 'optional',
            })
    ]

    field_sizes = {
        'category': 'col-md-3',
        'pages': 'col-md-3',
    }


#
# Workflow
#
class talk(SimpleRecordDeposition):
    name = _("Talk")
    name_plural = _("Talks")
    group = _("Talks & Slides")
    draft_definitions = {
        'default': TalkForm,
    }

    @classmethod
    def process_sip_metadata(cls, deposition, metadata):
        # Map keywords to match jsonalchemy configuration
        metadata['keywords'] = map(
            lambda x: {'term': x},
            metadata['keywords']
        )
