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

"""CDS Demosite interface."""

from flask import Blueprint
from invenio.ext.template.context_processor import template_args
from invenio.modules.search.views.search import collection as _collection

blueprint = Blueprint('cds', __name__, url_prefix='/',
                      template_folder='templates', static_folder='static')

from wtforms import TextField
from wtforms import FormField, SelectField, SelectMultipleField, StringField
from wtforms import Form as WTFormDefault

class TestForm(WTFormDefault):
	 keywords = StringField('Keywords')

	 topic =SelectField(u'Learning Topic', 
            choices=[('', 'Any'), ('cosmicwave', 'Cosmicwave'),('dark energy', 'Dark Energy'),('dark matter', 'Dark Matter'), ('multi dimensions', 'Multi Dimensions'),('forces', 'Forces'),('higgs boson', 'Higgs Boson'), ('w z bosons', 'W Z Bosons'),('masse', 'Masse'),('matter/antimatter', 'Matter / Antimatter'), ('black holes', 'Black Holes'),('neutrinos', 'Neutrinos'),('new physics', 'New Physics'), ('particles', 'Particles'),('quark', 'Quark'),('gluon', 'Gluon'), ('plasma', 'Plasma'),('standard model', 'Standard model'),('susy', 'SUSY'), ('technology', 'Technology'),('accelerators', 'Accelerators'),('calorimetry', 'Calorimetry'), ('engineering', 'Engineering'),('construction', 'Construction'),('computing', 'Computing'), ('grid', 'Grid'),('detectors', 'Detectors'), ('magnets', 'Magnets'),('particle', 'Particle'),('collaboration', 'Collaboration'), ('history', 'History'),('life as a physicist', 'Life as a Physicist'),('maps', 'Maps'), ('discovery', 'Discovery'),('industry', 'Industry'),('cancer treatment', 'Cancer Treatment'), ('culture', 'Culture'),('education', 'Education'),('medical applications', 'Medical Applications'), ('meddical screening', 'Meddical Screening')])
	 
	 audien =SelectField(u'Audience', 
            choices=[('', 'Any'), ('families', 'Families'),('journalists', 'Journalists'),('visitors', 'Visitors'), ('6-12 years', 'Children (6 to 12 years)'),('12-15 years', 'Teenagers (12 to 15 years)'),('16-25 years','Young adults (16 to 25 years)'),('physics teachers','Physics Teachers'),('teachers','Teachers'),('animators','Animators')])
	 item_type =SelectField(u'Item type', 
            choices=[('', 'Any'), ('document', 'Document'),('poster', 'Poster'),('video', 'Video'), ('audio', 'Audio'),('program', 'Program')])
	 availability =SelectField(u'Availability', 
            choices=[('', 'Any'), ('2', 'To build yourself'),('download', 'To download'),('4', 'To have for free but not downloadable'), ('5', 'To rent'),('6', 'To borrow'),('7','To buy')])
	 duration =SelectField(u'Duration', 
            choices=[('', 'Any'), ('0-5 min', '0-5 minutes'),('6-15 min', '6-15 minutes'),('16-30 min', '16-30 minutes'), ('31-45 min', '31-45 minutes'),('46-60 min', '46-60 minutes'),('>60 min', 'More than 60 minutes')])
	 language =SelectField(u'Language', 
           choices=[('', 'Any'), ('eng', 'Engish')])
	 
@template_args(_collection)
def collection_context():
    return dict(form=TestForm(csrf_enabled=False) )
