# -*- coding: utf-8 -*-
#
# This file is part of Invenio
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
# along with Invenio; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Test cds dojson video records."""

from __future__ import absolute_import

from invenio.testsuite import InvenioTestCase, make_test_suite, run_test_suite

CDS_DEMO_RECORDS = """
<record>
  <datafield tag="856" ind1="4" ind2=" ">
    <subfield code="u">http://library.web.cern.ch/library/Archives/isad/isakjohnsen.html</subfield>
    <subfield code="y">Higher level description</subfield>
  </datafield>
  <datafield tag="960" ind1=" " ind2=" ">
    <subfield code="a">01</subfield>
  </datafield>
  <datafield tag="852" ind1=" " ind2=" ">
    <subfield code="a">CERN Archives. Bldg. 61-S-001</subfield>
    <subfield code="c">J0912</subfield>
  </datafield>
  <datafield tag="300" ind1=" " ind2=" ">
    <subfield code="a">8 cm</subfield>
  </datafield>
  <datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">ARC010315</subfield>
  </datafield>
  <datafield tag="710" ind1=" " ind2=" ">
    <subfield code="a">CERN. Geneva. Proton Synchrotron Division (PS)</subfield>
  </datafield>
  <datafield tag="245" ind1=" " ind2=" ">
    <subfield code="a">Johnsen Kjell</subfield>
    <subfield code="b">Slides</subfield>
  </datafield>
  <datafield tag="541" ind1=" " ind2=" ">
    <subfield code="d">2011-05-01</subfield>
    <subfield code="f">Mrs Johnsen</subfield>
  </datafield>
  <datafield tag="340" ind1=" " ind2=" ">
    <subfield code="a">Slide</subfield>
  </datafield>
  <datafield tag="490" ind1=" " ind2=" ">
    <subfield code="a">CERN-ARCH-KJ</subfield>
    <subfield code="v">Collection: Kjell Johnsen</subfield>
  </datafield>
  <datafield tag="720" ind1=" " ind2=" ">
    <subfield code="a">Johnsen, Kjell</subfield>
  </datafield>
  <datafield tag="506" ind1=" " ind2=" ">
    <subfield code="a">Restricted</subfield>
  </datafield>
  <datafield tag="595" ind1=" " ind2=" ">
    <subfield code="a">1.03.15</subfield>
  </datafield>
  <datafield tag="916" ind1=" " ind2=" ">
    <subfield code="w">201148</subfield>
  </datafield>
  <datafield tag="925" ind1=" " ind2=" ">
    <subfield code="a">No date</subfield>
  </datafield>
  <datafield tag="041" ind1=" " ind2=" ">
    <subfield code="a">eng</subfield>
  </datafield>
  <datafield tag="927" ind1=" " ind2=" ">
    <subfield code="a">CERN-ARCH-KJ-140</subfield>
  </datafield>
</record>
"""


class TestCDSDoJSONMARC21(InvenioTestCase):

    """Test CDS."""

    def test_record_convert(self):
        """Test record loading from XML."""
        from dojson.contrib.marc21.utils import create_record
        from cds.base.dojson.marc21 import query_matcher
        from cds.base.dojson.marc21.translations.default import (
            translation as _translation
        )

        match = query_matcher(create_record(CDS_DEMO_RECORDS))

        # The match no matter what needs to be instance of
        # :class:`~cds.base.dojson.marc21.translations.default.CDSMarc21`
        self.assertIsInstance(
            match,
            _translation.__class__
        )

TEST_SUITE = make_test_suite(TestCDSDoJSONMARC21)

if __name__ == "__main__":
    run_test_suite(TEST_SUITE)
