# Analysis to map current MarcXML fields to the CDS Videos


| Name                                              | MarcXML Tag/Code       | Videos Data Model                 | Required  | Notes                                                                                   |
| ------------------------------------------------- | ---------------------- | --------------------------------- | --------- | ------------------------------------------------------------------------------------------ |
| Description                                       | 520__a                 | description                       | Yes       | Use the title if the record doesn't have a description.                                                   |
| Title                                             | 245__a                 | title.title                       | Yes       |                                                                                            |
| Access                                            | 506__d                 | access.read                       | No        | Restrict the record and provide access to authorized individuals or e-groups.             |
| Language                                          | 041__a                 | language                          | Yes       | Language of the record                                                                     |
| Keywords                                          | 653__a                 | keywords                          | No        |                                                                                    |
| DOI                                               | 0247_a                 | doi                               | No        | Digital Object Identifier                                                                  |
| Author/ Contributor                               | 700__a                 | contributor.name                  | Yes       | Name of the contributor for the video.                                                                 |
| Author/ Contributor                               | 700__e                 | contributor.role                  | Yes       | Contributor role. To be updated as optional.                                            |
| Author/ Contributor                               | 700__u                 | Not exist                         | Not exist | New field for contributor affiliation.                                           |
| Submitter                                         | 859__f, 856__f         | access.update/ deposit.created_by | Yes       | To be decided with the webcast team.                                                       |
| Date                                              | 518__d/ 269__c         | date                              | Yes       | Guess the correct date and keep the entire XML record attched.                             |
| Category/ Collection                              | ??                     | category                          | Yes       |                                                                                            |
| Video Type                                        | ??                     | type                              | Yes       |                                                                                            |
| Files (Videos, poster, subtitle)                  | 8564_, 8567_           | _files                            | Yes       | Video files will be decided with the webcast team.                                          |
| Indico                                            | 8564_y, 8564_u, 970__a | related_links                     | No        | Indico link will be added as `Related Links`.                                               |
| Copyright/ License                                | 540__/ 542__f          | license                           | No        | `URL` field will be added to the License, `statement` field will be added to the Copyright. |
| Report Number                                     | 088__a                 | report_number                     | No        | Only old videos (digitised) do have it.                                                    |
| Corporate Author                                  | 110__a                 | Not exist                         | Not exist | Not needed if hardcoded.                                                                  |
| Note                                              | 500__a                 | Not exist                         | Not exist | Will be added as a hidden field `internal_note`.                                            |
| Conference/ Presented at                          | 962__b                 | Not exist                         | Not exist | New fields for conference information.                                               |
| Published in                                      | 773__                  | Not exist                         | Not exist | New fields for conference information.                                                |
| Number of pages                                   | 300__a                 | Not exist                         | Not exist | Will be checked with the webcast team.                                                      |
| Collaboration                                     | 710__g                 | Not exist                         | Not exist | Add a new role to Contributors.                                                             |
| Related document                                  | 7870_                  | Not exist                         | Not exist | Will be `related works` as it’s done in CDS-RDM.                                           |
| Edition                                           | 250__a                 | Not exist                         | Not exist | Will be dropped if is the same with the date/year.                                          |
| Accelerator, Facility, Experiment, Project, Study | 693__                  | Not exist                         | Not exist | Will be added as `custom fields`.                                                           |
| Extra Title                                       | 246__a                 | Not exist                         | Not exist | Will be added as `additional titles`.                                                       |
| Volume                                            | 246__n & 246__p        | Not exist                         | Not exist | Will be append at the end of the description.                                               |
| Document contact                                  | 270__p                 | Not exist                         | Not exist | Will be added as contributor with correct role.                                             |
| French Description                                | 590__a                 | Not exist                         | Not exist | Will be added as additional description as done in RDM.                                     |
| Video Location                                    | 518__r, 111__c         | Not exist                         | Not exist | Location will be added as a new field.                                                      |

## Metadata

### ✅ Description

**Decision:** If the record mising description, use the title.

```xml=
<datafield tag="520" ind1=" " ind2=" ">
    <subfield code="a"><!--HTML--><p>...description</p></subfield>
</datafield>
```

- Not all records has a description, but it's required for CDS Videos, example [record](https://cds.cern.ch/record/2719117) without description (indico conference record)
    - The [metadata](https://cernbox.cern.ch/s/k9KekzQvBm8Rp7l) from indico, their description is `""`


### ✅❓ Contributors
- `700`: contribution_speakers
- `906`: event_speakers
- `100`: MAIN ENTRY--PERSONAL NAME  (NR) [CERN] (Also contrubitor) / Speaker
- `511`: Is an author with role performer or participant.


#### Decisisons:
- Role: Change to not mandatory.
    - TODO: Check that when we mint DOI we use creators instead contributors, if not we need to re-check this solution. Checked, we serialize it as creators.
- Affiliation: Add new field, to be seen if data is normalized
    - For names that have a wrong format and we migrate them as they are, these values need to be curated in the future.
- For contributors, we don't keep the ID (#BEARD), only migrate the name and role.



```xml=
<datafield tag="700" ind1=" " ind2=" ">
    <subfield code="a">Fardelli, Giulia</subfield>
    <subfield code="e">speaker</subfield>
    <subfield code="u">Boston U.</subfield>
</datafield>  
```
[example](https://cds.cern.ch/record/332604/export/xm?ln=en)
```xml=
<datafield tag="700" ind1=" " ind2=" ">
    <subfield code="0">AUTHOR|(CDS)2083955</subfield> // CERN People Record
    <subfield code="9">#BEARD#</subfield>
    <subfield code="a">Veneziano, Gabriele</subfield>
    <subfield code="e">speaker</subfield>
</datafield>
```


**Speaker:** [example](https://cds.cern.ch/record/43728)
- In this [record](https://cds.cern.ch/record/254588/) `100__a` shown as Author? `Defined as creator in legacy`

    ```xml=
    <datafield tag="100" ind1=" " ind2=" ">
    <subfield code="a">Maiani, Luciano</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/2231952)
    ```xml=
    <datafield tag="100" ind1=" " ind2=" ">
        <subfield code="a">Hey, Anthony J G</subfield>
        <subfield code="e">speaker</subfield>
    </datafield>
    ```

Extra Contributors? (Not shown) [example](https://cds.cern.ch/record/1710564)
```xml=
<datafield tag="906" ind1=" " ind2=" ">
    <subfield code="p">Fardelli, Giulia</subfield>
    <subfield code="u">Boston U.</subfield>
</datafield>
<datafield tag="906" ind1=" " ind2=" ">
    <subfield code="p">Apollinari, Giorgio</subfield>
    <subfield code="u">Fermi National Accelerator Laboratory (FNAL)</subfield>
</datafield>
<datafield tag="906" ind1=" " ind2=" ">
    <subfield code="p">Parente, Claudia</subfield>
    <subfield code="u">CERN</subfield>
</datafield>
```    

**511 Tag** looks like a contributor? not displaying
- [example](https://cds.cern.ch/record/529984/export/xm?ln=en)
    ```xml=
    <datafield tag="511" ind1=" " ind2=" ">
        <subfield code="a">Larbalestier, David C</subfield>
        <subfield code="e">speaker</subfield>
        <subfield code="u">Univ. Wisconsin</subfield>
    </datafield>
    ``` 


### ✅❓Access
#### ❓Update

**Decisions:**
- Needs discussion with webcast team to decide who has to curate this, and this person(s) would be the owner. Metadata curator for multimedia? Use system user as owner and grant edit rights to an e-group?
- `856__f` and `859__f` are submitter


**Submitted by:** [example record](https://cds.cern.ch/record/2919303)
- Indico metadata also has this as `event creator`
- Should it be metadata._deposit.created_by or deposit_owners? or contributor?
    - If we decide to keep in `metadata._deposit.created_by`, this is id of the person, how can we keep it and what if person does not have id? [example](https://sandbox-videos.web.cern.ch/api/deposits/video/502ffe05e5fa4788b2cecf2279ec3a2c)
```xml=
<datafield tag="859" ind1=" " ind2=" ">
<subfield code="f">ethan.martin.torres@cern.ch</subfield>
</datafield>
```
**Some records don’t have: [example1](https://cds.cern.ch/record/425290), [example2](https://cds.cern.ch/record/436401)** CERN Digital Memory project? 

Not shown, [example](https://cds.cern.ch/record/43728)

```xml=
<datafield tag="856" ind1="0" ind2=" ">
    <subfield code="f">Tony.Shave@cern.ch</subfield>
</datafield>
```


#### ✅ Read (Restricted)

```xml=
<datafield tag="506" ind1="1" ind2=" ">
    <subfield code="a">Restricted</subfield>
    <subfield code="d">internal-audit-staff [CERN]</subfield>
    <subfield code="d">indico-atlas-managers [CERN]</subfield>
    <subfield code="f">group</subfield>
    <subfield code="2">CDS Invenio</subfield>
    <subfield code="5">SzGeCERN</subfield>
</datafield>
<datafield tag="506" ind1="1" ind2=" ">
    <subfield code="a">Restricted</subfield>
    <subfield code="d">email@cern.ch</subfield>
    <subfield code="f">email</subfield>
    <subfield code="2">CDS Invenio</subfield>
    <subfield code="5">SzGeCERN</subfield>
</datafield>
```
### Category/Type Keywords?

- **DECISION:** 
    - Category: CERN
    - Type: Lectures
    - Keep CERN category, add the web lecture type and restrict this type to a e-group.

Proposed Solution:
* Category: Lectures & Events
* Type: Collection

#### Tag 980 Collection Indicator
**Decision:** 
- To be checekd if we add a new category or simply a type (that would be restricted). Add a new field with the collections array, and create the tree structure as done for press.
- This need more discussion.

[example:](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">VIDEOARC</subfield>
</datafield>
<datafield tag="980" ind1=" " ind2=" ">
    <subfield code="a">Indico</subfield>
    <subfield code="b">SSW</subfield>
</datafield>
```
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en)
    - tag 980__a, primary collection indicator
    - tag 980__b, secondary collection indicator
    - tag 980__c, deleted (do we need it?)

- [CDS MARC21:](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L407)
     - tag 980, subfield code a for cds categories
     - tag 980, subfield code b for cds categories

- [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L111)
    ```xml=
    <datafield tag="980" ind1=" " ind2=" ">
        <!-- HARDCODED -->
        <subfield code="a">Indico</subfield>
    </datafield>
    <!--
    <datafield tag="980" ind1=" " ind2=" ">
        <subfield code="b">TALK</subfield>
    </datafield>
    -->
    ```
#### Tag 650 SUBJECT ADDED ENTRY/Subject category: 
Can be used as keyword?  We have a lot of values. [example record](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="650" ind1="1" ind2="7">
    <subfield code="2">SzGeCERN</subfield>
    <subfield code="a">Detectors and Experimental Techniques</subfield>
</datafield>
```
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en)
    *  $a   Topical term or geographic name (NR) - [CER,MAN,MMD]
    *  $2   Source of heading or term  (NR) - [CER,MAN,MMD]
    *  $e   description to be displayed (default: keyword) (NR) - [CER]

- [CDS MARC21:](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L407)
     - tag 650, ind1 = 1, ind2 = 7, subfield code a for category

- [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L111)
    ```xml=
    <datafield tag="650" ind1="1" ind2="7">
        <!-- <subfield code="a">TH Theoretical Seminar</subfield> -->
    </datafield>
    <datafield tag="650" ind1="2" ind2="7">
        <!-- HARDCODED -->
        <subfield code="a">Event</subfield>
    </datafield>

    ```
possible values in cds:
```
  Code a: ['Nuclear Physics', 'Academic Training Lecture For Postgraduate Students', 'CPT General Meetings', 'Open meetings', 'Physics weeks', 'Tutorials', 'Seminars/Workshops', 'Conferences, Workshops & Schools', 'Library events', 'QTI Lectures and Seminars', '... +412 more values']
  Code 2: ['SzGeCERN']
```

#### Tag 080 Subject code?
We don't have much values for the subject code. Possible values in cds:
- Code a: ['92'(3 [record](https://cds.cern.ch/record/1206221)), '539.1.072'(1 [record](https://cds.cern.ch/record/254588))]

[example record](https://cds.cern.ch/record/254588)
```xml=
<datafield tag="080" ind1=" " ind2=" ">
    <subfield code="a">539.171.01</subfield>
</datafield>
```

- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) 080 UNIVERSAL DECIMAL CLASSIFICATION NUMBER (R)
    - $a   Universal Decimal Classification number (NR) - [CER,WAI/UDC]

#### Tag 690 - SUBJECT INDICATOR
Can be used as keywords. We have specific values(Checked)
- possible values in cds:
    - Code a: ['SSLP', 'ACAD', 'CERN', 'reviewed', 'movingimages', 'quality-controlled', 'TALK']
    - Code 9: ['CERN QA', 'review']
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) SUBJECT INDICATOR
    - $a   Term (NR) - [ARC,CER,IEX,MAN,MMD]

- [CDS MARC21:](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L482)
    ```python=
    # insert after the tag LAST 690
    el = self.document.xpath('/record/datafield[@tag="690"]')[-1]
    p = el.getparent()
    p.insert(p.index(el)+1, new_el)
    ```
- [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L61)
    ```xml=
    <datafield tag="690" ind1="C" ind2=" ">
        <!-- HARDCODED -->
        <subfield code="a">TALK</subfield>
    </datafield>
    <datafield tag="690" ind1="C" ind2=" ">
        <!-- HARDCODED -->
        <subfield code="a">CERN</subfield>
    </datafield>
    ```



[example:](https://cds.cern.ch/record/2920218)
```xml=
<datafield tag="690" ind1="C" ind2=" ">
    <subfield code="a">TALK</subfield>
</datafield>
<datafield tag="690" ind1="C" ind2=" ">
    <subfield code="a">CERN</subfield>
</datafield>
```

#### 490 Series Statement
There can be multiple series. `490__a` looks like subcategory, can be used as keyword? We have a lot of values(Checked the production more than 1k values)

```
Possible values for tag:490:
  Code a: ['OpenStack Day CERN - "Accelerating Science with OpenStack"', 'ATLAS Collaboration Week "Towards Run 3"', 'Technology and Market Trends for the Data Centre', 'Naples WLCG Workshop Summary', 'Stefan Lueders: Computer security in 2021', "Axel Naumann: Best practices: the theoretical and practical underpinnings of writing code that's less bad", 'ATLAS Week: The First 13 TeV Data!', 'DPA-IT Talk', 'CS technical forums', 'Particle World - Q&A', '... +1526 more values']
  Code v: ['2000-2009', '2000-2001', '2002-2003', '289', '288', '346', '347', '340', '341', '342', '... +197 more values']
```
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) SERIES STATEMENT
    - $a   Series statement (NR) - [CER]
    - $v   Volume/sequential designation (NR) - [CER]

- [CDS MARC21:](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L422)
    - tag 490, subfield code a for category (and with series years)
- [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L43)
    ```xml=
    <datafield tag="490" ind1=" " ind2=" ">
        <!-- <subfield code="a">TH Theoretical Seminar</subfield> -->
    </datafield>
    ```
[example:](https://cds.cern.ch/record/2918042)
```xml=
<datafield tag="490" ind1=" " ind2=" ">
    <subfield code="a">KT Seminars</subfield>
</datafield>
<datafield tag="490" ind1=" " ind2=" ">
    <subfield code="a">CERN Venture Connect Summit 2024</subfield>
</datafield>
```

### Keywords: 6531_a 
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) SERIES STATEMENT
    - Keywords 6531 $a

[example 1](https://cds.cern.ch/record/113916)
```xml=
<datafield tag="653" ind1="1" ind2=" ">
    <subfield code="9">CERN</subfield>
    <subfield code="a">LHC</subfield>
</datafield>
```
[example 2](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="653" ind1="1" ind2=" ">
    <subfield code="9">review</subfield>
    <subfield code="a">Computer</subfield>
</datafield>
<datafield tag="653" ind1="1" ind2=" ">
    <subfield code="9">review</subfield>
    <subfield code="a">Monte Carlo</subfield>
</datafield>
<datafield tag="653" ind1="1" ind2=" ">
    <subfield code="9">review</subfield>
    <subfield code="a">Simulation</subfield>
</datafield>
```

### ✅❓Date 
- `260__c`: Year
- `269__c`: Date only 
- `518__d`: Full date time (with hour)
- `961__x`: creation date, `961__c`: modification date

#### Decision: 
- Guess the correct date and keep the entire XML record attched.
- Add a new field to keep the location. Check in datacite for the field name/type.
- TODO: Check with webcast team about this date and the "number of pages" that appear on the same field in CDS.

#### Questions
- Indico event metadata have the event date (start date and end date), maybe we can get the date from indico? [example](https://cds.cern.ch/record/883191)
- They're not in the same format?
Lecture note:
```xml=
<datafield tag="518" ind1=" " ind2=" ">
    <subfield code="d">2024-11-19T14:00:00</subfield>
</datafield>
```
[example](https://cds.cern.ch/record/423817) shown like: `Talk on 25 Jan 2006 in Main Auditorium`
```xml=
<datafield tag="518" ind1=" " ind2=" ">
    <subfield code="d">25 Jan 2006</subfield>
    <subfield code="g">a06146</subfield>
    <subfield code="r">Main Auditorium</subfield>
</datafield>
```
```xml=
<datafield tag="518" ind1=" " ind2=" ">
    <subfield code="a">CERN, Geneva, 23 - 27 Nov 1998</subfield>
</datafield>
```

**Imprint:**
Usually `269__c` used in imprint for the date but they are not on same format. [Example](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="269" ind1=" " ind2=" ">
    <subfield code="c">1993-08-09</subfield>
</datafield>
```

```xml=
<datafield tag="260" ind1=" " ind2=" ">
    <subfield code="a">Geneva</subfield>
    <subfield code="b">CERN</subfield>
    <subfield code="c">1998</subfield>
</datafield>
```

```xml=
<datafield tag="269" ind1=" " ind2=" ">
    <subfield code="a">Geneva</subfield>
    <subfield code="b">CERN</subfield>
    <subfield code="c">2005</subfield>
</datafield>
```


### ✅ Title
```xml=
<datafield tag="245" ind1=" " ind2=" ">
    <subfield code="a">Holography and Regge Phases at Large U(1) Charge</subfield>
</datafield>
```
-  Some records has `b`, [example](https://cds.cern.ch/record/43728)
    ```xml=
    <datafield tag="245" ind1=" " ind2=" ">
        <subfield code="a">Director General's Report to Council</subfield>
        <subfield code="b">report, CERN, Geneva, 15 Dec 2000</subfield>
    </datafield>
    ```

### ✅ Language
```xml=
<datafield tag="041" ind1=" " ind2=" ">
    <subfield code="a">eng</subfield>
</datafield>
```

### Files
```xml=
<datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">https://lecturemedia.cern.ch/2024/1401254/1401254-presenter-1080p-quality.mp4</subfield>
    <subfield code="x">video/mp4</subfield>
    <subfield code="y">Content: presenter. Resolution: 1920x1080. Baudrate: 3238446</subfield>
</datafield>
```
[example](https://cds.cern.ch/record/349042/)
```xml=
<datafield tag="856" ind1="4" ind2=" ">
    <subfield code="u">http://cds.cern.ch/record/349042/files/AT00000495.tif</subfield>
    <subfield code="y">Transparencies</subfield>
    <subfield code="s">1595668</subfield>
</datafield>
```

### Poster for the video
- [ ]  Might be uploaded with REST API (investigate) (works but gives an error in CDS Videos)

[example record](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">https://lecturemedia.cern.ch/1993/CERN-VIDEO-C-93-08/CERN-VIDEO-C-93-08-posterframe-480x360-at-0-percent.jpg</subfield>
    <subfield code="x">pngthumbnail</subfield>
    <subfield code="y">thumbnail weblecture</subfield>
</datafield>
```

### Subtitles:
- [ ]  Might be uploaded with REST API (investigate)(works but gives an error in CDS Videos(I'm uploading and empty vtt file))

Example [record](https://cds.cern.ch/record/2881756)
```xml=
<datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">/2018/716207/716207_en.vtt</subfield>
    <subfield code="x">subtitle</subfield>
    <subfield code="y">subtitle English</subfield>
</datafield>
<datafield tag="856" ind1="7" ind2=" ">
    <subfield code="2">MediaArchive</subfield>
    <subfield code="u">/2018/716207/716207_fr.vtt</subfield>
    <subfield code="x">subtitle</subfield>
    <subfield code="y">subtitle Français</subfield>
</datafield>
```

### ✅ DOI

- DOI can be added with the video metadata

[example1](https://cds.cern.ch/record/108704) [example2](https://cds.cern.ch/record/2767144)
```xml=
<datafield tag="024" ind1="7" ind2=" ">
    <subfield code="2">DOI</subfield>
    <subfield code="a">10.5170/CERN-1965-041</subfield>
    <subfield code="q">ebook</subfield>
</datafield>
```

### ✅❓Report Number

#### Decision:
- only old videos (digitised) do have it.
- Question(Zubeyde): Did we decided to not keep it?
    - Migrate as alternative identifier with scheme CDS Reference

How can we add to CDS Videos? It allows to reserve report number but only for existing projects:
- `Enter project number (e.g. for CERN-VIDEO-001, enter 001) or leave it empty if no project yet.`
    - `Not existent project number`
- It's only for the category `CERN`?

[example](https://cds.cern.ch/record/108704/)

```xml=
<datafield tag="088" ind1=" " ind2=" ">
    <subfield code="a">CERN-65-41</subfield>
</datafield>
```
`088__9` not shown: [example](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="088" ind1=" " ind2=" ">
    <subfield code="9">CERN-VIDEO-C-93-08</subfield>
</datafield>
```
`088__z` not shown: [example](https://cds.cern.ch/record/281782/)
```xml=
<datafield tag="088" ind1=" " ind2=" ">
    <subfield code="9">CM-B00031253</subfield>
    <subfield code="z">1/3</subfield>
</datafield>
```

## Missing

### ✅ Indico
**Decision:** Add as `Related Links` and use the event id as `Alternative Identifiers`
```xml=
<datafield tag="856" ind1="4" ind2=" ">
    <subfield code="u">https://indico.cern.ch/event/1447077/</subfield>
    <subfield code="y">Event details</subfield>
</datafield>

<datafield tag="856" ind1="4" ind2=" ">
    <subfield code="u">https://indico.cern.ch/event/1439460/contributions/6057166/</subfield>
    <subfield code="y">Talk details</subfield>
</datafield>

<datafield tag="970" ind1=" " ind2=" ">
    <subfield code="a">INDICO.1447077</subfield>
</datafield>

<datafield tag="084" ind1=" " ind2=" ">
    <subfield code="2">Indico</subfield>
    <subfield code="a">104</subfield>
</datafield>
```

exception for `970__a` [record](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="970" ind1=" " ind2=" ">
    <subfield code="a">000171261CER</subfield>
</datafield>
```

### ✅ Document contact?
DECISION: Add as a contributor with a correct role

Example [record](https://cds.cern.ch/record/2895265)

- Could be added to contributors? with a new role
```xml=
<datafield tag="270" ind1=" " ind2=" ">
    <subfield code="p">Urs Wiedemann</subfield>
</datafield>
```

### ✅❓Corporate author:

#### DECISION: 
- Check if it is hardcoded, if yes, not needed.
    - Checked, it's hardcoded [here](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L7) in the old `opencast to cds marc` but not in the current one, and these are the values in cds:
        ```
            Possible values for tag:110:
              Code a: ['CERN. Geneva HR-FAS', 'CERN, Geneva', 'CERN. Geneva HR-RFA', 'CERN. Geneva. Audiovisual Unit', 'WHO/OMS Geneva', 'CERN. Geneva']
        ```

[example](https://cds.cern.ch/record/2153143/)
```xml=
<datafield tag="110" ind1=" " ind2=" ">
    <subfield code="a">CERN. Geneva</subfield>
</datafield>
```

If possible add it as a creator (role TBD), otherwise to be added to the _curation/_migration field.

### ✅ Note
[example](https://cds.cern.ch/record/883191)

#### DECISION:
- Add it to a hidden field `internal_note`, 

Could be added at the end of the description like `Note: ` or do we need a separate field?

```xml=
<datafield tag="500" ind1=" " ind2=" ">
    <subfield code="a">CERN, Geneva, 16 Sep 2005</subfield>
</datafield>
<datafield tag="500" ind1=" " ind2=" ">
    <subfield code="a">Friday 16 September, 09.00-11.00, Main Auditorium</subfield>
</datafield>
```

Multiple notes: [example](https://cds.cern.ch/record/422919)
```xml=
<datafield tag="500" ind1=" " ind2=" ">
<subfield code="9">curation</subfield>
<subfield code="a">The video was reviewed and enriched with additional information.</subfield>
</datafield>
<datafield tag="500" ind1=" " ind2=" ">
<subfield code="9">curated_title</subfield>
<subfield code="a">Title: The Status of High-Temperature Superconductivity</subfield>
</datafield>
<datafield tag="500" ind1=" " ind2=" ">
<subfield code="9">curated_type</subfield>
<subfield code="a">Type: Conference Speech</subfield>
</datafield>
```

### ✅ Presented at

#### DECISION: 
- Add conference information fields, to be able to search by them. Add PID? 

#### Proposed solution:
- Enhance related links to match `RelatedIdentifier` datacite schema field by adding the required fields and use this one with `relationType` `isPartOf` to reference the conference.
- Adding the dates field to support different dates and add this value as `Other` with text "Presented at <URL>" alongside the conference date. 
- TODO:
    - Check how related links are using when minting doi

#### Analysis
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) ALEPH Linking Field
    - $b - sysno of the linked document record (NR) - [ARC,CER,MMD]
    - $n - note regarding a DN (down record) link - (NR) [ARC,CER]
- [micala xml](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L406/):
    - if is_conference, tag 962, subfield code n for series

Some [records](https://cds.cern.ch/record/423033) connected with conferences(Books & Proceedings?) [`Contributions to this conference in CDS`](https://cds.cern.ch/record/238397)

```xml=
<datafield tag="962" ind1=" " ind2=" ">
    <subfield code="b">238397</subfield> // Conference record id
    <subfield code="n">geneva910725.2</subfield>
</datafield>
```

### ✅ Published in

**DECISION:** Add conference information fields, to be able to search by them. Add PID?

- 773   HOST ITEM ENTRY (R) [CERN]
    - `773__a`: DOI
    - `773__p`: Title (NR) - [ARC,CER,MMD]
    - `773__u`: URL (NR) - [MMD]
- Proposed solution:
    - Can be used in `metadata/related_links`
    - Enhance related links to match `RelatedIdentifier` datacite schema field by adding the required fields and use this one with `relationType` `isPartOf` to reference the conference.
    - Adding the dates field to support different dates and add this value as `Other` with text "Presented at <URL>" alongside the conference date.
- TODO:
    - Check how related links are using when minting doi
    
Article connected [record](https://cds.cern.ch/record/254588/) from the UI shown as `Published in:`

```xml=
<datafield tag="773" ind1=" " ind2=" ">
    <subfield code="p">The GISMO project</subfield>
    <subfield code="u">http://cdsweb.cern.ch/record/253533?ln=en</subfield>
</datafield>
```
[This one](https://cds.cern.ch/record/423005) also shown `published in`, it's opens the doi website but link is broken?
```xml=
<datafield tag="773" ind1=" " ind2=" ">
    <subfield code="a">2276207</subfield>
</datafield>
```


### ✅❓Number of pages 

**Decision:**  It is the duration in data.json [record](https://cds.cern.ch/record/423817), [data.json](https://lecturemedia.cern.ch/2006/a06146/data.v2.json) Should We drop it?
    
Shown in `Imprint` in UI (date - number of pages)
```xml=
<datafield tag="300" ind1=" " ind2=" ">
    <subfield code="a">209</subfield>
</datafield>
```

### ✅Collaboration 

#### DECISION: 
- Add a new role to `Contributors`, name should be ResearchGroup or maybe Collaboration (it shoud be serialized as contributor)
    - We should to change surname, name for the `not CERN contributor`

#### Analysis 
`710__g` shown as `Collaboration` [example record](https://cds.cern.ch/record/254588/)

- `710`: ADDED ENTRY--CORPORATE NAME  (R) [CERN]
    * $a   Corporate name (NR) - [ARC,CER,MAN]
    * $g   Collaboration  (NR) - [CER]
    * $5   CERN Paper (NR) - [CER,MAN,MMD]
    
    
```xml=
<datafield tag="710" ind1=" " ind2=" ">
    <subfield code="5">EP</subfield>
</datafield>
<datafield tag="710" ind1=" " ind2=" ">
    <subfield code="g">GISMO Collaboration</subfield>
</datafield>
```
[example](https://cds.cern.ch/record/281782)
```xml=
<datafield tag="710" ind1=" " ind2=" ">
    <subfield code="a">CERN. Geneva</subfield>
</datafield>
```


### ✅ Accelerator/Facility, Experiment, Project, Study

**DECISION:** Add them as "custom fields", same format/style as in CDS.

- `693`: ACCELERATOR/EXPERIMENT (R) [CERN]
    - $a   Accelerator (NR) - [CER,IEX,MMD]
    - $e   Experiment (NR) - [CER,IEX,MAN,MMD]
    - $p   Project
    - $s   Study

- Proposed Solution:
    - All of them can be keyword
    
[example](https://cds.cern.ch/record/113916)
```xml=
<datafield tag="693" ind1=" " ind2=" ">
    <subfield code="a">CERN LEP</subfield>
</datafield>
```
**Project:** `693__p` [example](https://cds.cern.ch/record/1103473)
```xml=
<datafield tag="693" ind1=" " ind2=" ">
    <subfield code="a">CERN ISOLDE</subfield>
    <subfield code="e">Not applicable</subfield>
    <subfield code="p">CERN HIE-ISOLDE</subfield>
</datafield>
```

**Study:** `693__s` [example](https://cds.cern.ch/record/2262655)
```xml=
<datafield tag="693" ind1=" " ind2=" ">
    <subfield code="s">CERN Gamma Factory</subfield>
</datafield>
```


### ✅❓ Copyright/License

#### DECISION:
- To check how many licenses are not CERN on videos, to understand if we can align this field with RDM, otherwise we could simply add the URL.
- Add URL to license.
- Add statement field to copyright. 
- Open question: Why in RDM we don't have the copyright statement field?
    
#### Analysis 
- `540`TERMS GOVERNING USE AND REPRODUCTION (LICENSE)
    *  $a   Terms governing use and reproduction, e.g. CC License
    *  $b   person or institution imposing the license (author, publisher)
    *  $u   URI
    *  $3   material (currently not used)
    
- Proposed Solution:
    - We can add licence but for the extra licences we only have `credit`, `license` and `material`
    - Question: How should we add the license?
    
[cds example](https://cds.cern.ch/record/2767311)
   ```xml=
<datafield tag="540" ind1=" " ind2=" ">
    <subfield code="3">publication</subfield>
    <subfield code="a">CC-BY-4.0</subfield>
    <subfield code="u">https://creativecommons.org/licenses/by/4.0/</subfield>
</datafield>
```
[example sandbox record with license](https://sandbox-videos.web.cern.ch/record/2292672)
Videos data model example:
```json=
{"license": [
    {
        "license": "CERN",
        "url": "http://copyright.web.cern.ch"
    },
    {
        "credit": "https://creativecommons.org/licenses/by/4.0",
        "license": "CC-BY-4.0",
        "material": "publication"
    }
    ],
}
```

In this [record](https://cds.cern.ch/record/2017328) `542__f` shown as `Copyright/License`
- `542` COPYRIGHT INFORMATION
    * $d   Copyright holder
    * $g   Copyright date
    * $f   Copyright statement as presented on the resource
    * $3   materials  (currently not used)
```xml=
<datafield tag="542" ind1=" " ind2=" ">
    <subfield code="d">CERN</subfield>
    <subfield code="f">ATLAS Experiment © 2014 CERN</subfield>
    <subfield code="g">2015</subfield>
</datafield>
```

### ✅ Related document

**DECISION:** Related links should become `related works` as it's done in CDS-RDM, for now related links will be "deprecated", no migration needed for now.

- Proposed solution:
    - Can be used in `metadata/related_links`
    - Enhance related links to match `RelatedIdentifier` datacite schema field by adding the required fields and use this one with [`relationType` `?`](https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/relatedidentifier/#b-relationtype) to reference the conference.

- `787` OTHER RELATIONSHIP ENTRY   (R)
    - Indicators
        - First   Note controller
            - 0 - Display note (in $i) 
            - 1 - Do not display note (We dont have any)
    - Subfield Code(s)
        * $i   Relationship information (R) - [CER]
        * $r   Report number
        * $w   Record control number (R) - [CER]

    
    
[example](https://cds.cern.ch/record/2767311)
shown `7870_i` `7870_r` and links to the record id `7870_w`
```xml=
<datafield tag="787" ind1="0" ind2=" ">
    <subfield code="i">Conference Paper</subfield>
    <subfield code="r">EPJ Web of Conferences 251, 03065 (2021)</subfield>
    <subfield code="w">2813802</subfield>
</datafield>
```

### ✅❓ Edition

#### DECISION:
- Try to check with a wider search query to get more records, drop it if still not many, Checked and decided to drop it
- Check how many records do have edition, if not many we can drop it
    - Production results:
        ```
        Record:558490 Edition (2001 ed.) and year (2002) are different
        275 of the 20710 records has edition
        ```
    
#### Analysis 
Is it the same with the date/year? If it is do we need to keep it?
[example](https://cds.cern.ch/record/1036201)
```xml=
<datafield tag="250" ind1=" " ind2=" ">
    <subfield code="a">2006 ed.</subfield>
</datafield>
```


### ✅ Extra Title and Volume

**DECISION:** Add additional titles as in RDM

- `246` VARYING FORM OF TITLE:1
    * $a   Title proper/short title (NR) - [CER not base=3n]
    * $b   Remainder of title (NR) - [CER not base=3n]
    * $g   Miscellaneous information  (NR) - [CER not base=3n]
    * $i   Display text  (NR) - [CER not base=3n]
    * $n   Number of part/section of a work (R) - [CER not base=3n]
    * $p   Name of part/section of a work (R) - [CER not base=3n]

    
- `246__` `Titre français` (246 n,p is also volume?)
    - [example](https://cds.cern.ch/record/422556/export/xm?ln=en)
    ```xml=
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="a">Le prestige du CERN</subfield>
        <subfield code="i">Titre français</subfield>
    </datafield>
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="a">Mégascience moderne et progrès technique</subfield>
        <subfield code="i">Titre français</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/423096)(shown as `Related title`)
    ```xml=
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="a">The RHIC experimental programme</subfield>
    </datafield>
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="a">HERA news</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/931352)
    ```xml=
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="a">APROM/RPROM/SPROM</subfield>
        <subfield code="b">Analysis, Reconstruction and Simulation</subfield>
    </datafield>
    ```
- `VOLUME` [example](https://cds.cern.ch/record/423084)(video not displaying)
    ```xml=
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="n">pt.1</subfield>
        <subfield code="p">CMS : a compact solenoidal detector for LHC</subfield>
    </datafield>
    <datafield tag="246" ind1=" " ind2=" ">
        <subfield code="n">pt.2</subfield>
        <subfield code="p">CMS : a compact solenoidal detector for LHC</subfield>
    </datafield>
    ```
**DECISION:**   
Append volume at the end of the description

### ✅ French Description
   
**DECISION:** Add as additional description as done in RDM.

- Proposed solution:
    - Can be used as the same (add it in the end of the description)
    - Can be added as translations `French` `Description`

- `590` FRENCH SUMMARY NOTE 
    *  $a   Summary, etc. note in French (NR) - [MMD]
    *  $b   Expansion of summary note in French (NR) - [MMD]

[example](https://cds.cern.ch/record/1205594)
They're displaying at the end of the description
```xml=
<datafield tag="590" ind1=" " ind2=" ">
    <subfield code="a">Le passage à la retraite représente la sortie du monde du travail et l'entrée dans une nouvelle période de vie. Cette période de transition, de changement est vécu différemment par chaque personne. Dans cette vidéo, enregistrée il y a quelques années, Dr. Sartorius de l'OMS rend des futurs retraités de son organisation attentifs aux changements qui les attend. Nous mettons cette vidéo à la disposition du personnel du CERN pour stimuler leur propre réflexion.</subfield>
</datafield>
```
    
## Missing? Not displaying Fields

### ✅ Tag 852 

**DECISION:** Add a `_curation`/`_internal`/`_cataloguing` (name TBD) and inside add physical location. TBD if we transform it to json format or keep as an XML

- `852` LOCATION
    - $a   Location  (NR) - [ARC,CER,MAN,MMD]
    - $c   Shelving location (NR) - [ARC,CER]

- [example](https://cds.cern.ch/record/254588/) 
    - 539.1.072 this number is also in the `080__a` and shows as `Subject Code`
    ```xml=
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="c">CERN Central Library</subfield>
        <subfield code="h">539.1.072 ATW</subfield>
    </datafield>
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="c">CERN Depot 1, bldg. 2 (DE1)</subfield>
        <subfield code="h">539.1.072 ATW Videotape</subfield>
    </datafield>
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="c">CERN Central Library</subfield>
        <subfield code="h">539.1.072 ATW Videotape</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/332604)
    ```xml=
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="a">60</subfield>
        <subfield code="b">Z0151</subfield>
        <subfield code="c">CM-A00000322</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/546253/export/xm?ln=en)
    ```xml=
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="a">Armoire F295 Bât 500</subfield>
        <subfield code="c">CM-A00000031</subfield>
        <subfield code="x">vhs</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/845134/export/xm?ln=en) (has only one video)
    ```xml=
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="9">Part I</subfield>
        <subfield code="a">510-R-036</subfield>
        <subfield code="c">CM-A00000010</subfield>
        <subfield code="x">DVD</subfield>
    </datafield>
    <datafield tag="852" ind1=" " ind2=" ">
        <subfield code="9">Part II</subfield>
        <subfield code="a">510-R-036</subfield>
        <subfield code="c">CM-A00000010</subfield>
        <subfield code="x">DVD</subfield>
    </datafield>
    ```

### ✅❓ 024 tag

**DECISION:** To be discussed, OAI. https://scivideos.org/source-repository/CERN-CDS (they are using Dublin core) we might need to add the set for this, alternative is that they harvest via search.

Most of them has this tag, can be keyword? oai?
- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) PHYSICAL MEDIUM
    - $a    OAI - [CER]
    - $p    OAI-set indicator - [CER]
```xml=
<datafield tag="024" ind1="8" ind2=" ">
    <subfield code="a">oai:cds.cern.ch:377090</subfield>
    <subfield code="p">cerncds:FULLTEXT</subfield>
    <subfield code="p">forSciTalks</subfield>
    <subfield code="p">cerncds:TALK</subfield>
    <subfield code="p">cerncds:TALK:FULLTEXT</subfield>
    <subfield code="p">cerncds:MEMORIAV</subfield>
</datafield>
```


### ✅❓ 773__r 

#### DECISION:
- To be checked how many values we have. (Looks like we only have two values with multiple records)
    - `2272638`: 23 records, [example](https://cds.cern.ch/record/423099) `2270587`: 4 records, [example](https://cds.cern.ch/record/1122259) this record also digitized and lecturemedia
- Seems that is a way to group the videos. One solution could be to use the title of the referenced record to be added as a keyword. Alternative is to add the videos as related items.

#### Analysis 
Normally it's defined `HOST ITEM ENTRY` in [here](https://cds.cern.ch/help/admin/howto-marc?ln=en) and shown as `Published in` but what is the `r`?
[example](https://cds.cern.ch/record/423096) it's a record id?
In legacy code: `REPORT_NUMBER_TOC_MARC = '773__r'`
```xml=
<datafield tag="773" ind1=" " ind2=" ">
    <subfield code="r">2272638</subfield> 
</datafield>
```
    
- Needs discussion on how we want to group the videos by event id?


### ✅ 340 Tag

**DECISION:** Drop streaming video, anything else we copy over to curation field.

- [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) PHYSICAL MEDIUM
    - $a   Material base and configuration (NR) - [ARC,CER,MAN,MMD]
    - $c   Materials applied to surface (NR) - [ARC]
    - $d   Information recording technique (NR) - [ARC]
    - $9   CD-ROM [code concatinated]

- [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L39)
    ```xml=
    <datafield tag="340" ind1=" " ind2=" ">
        <!-- HARDCODED -->
        <subfield code="a">Streaming video</subfield>
    </datafield>
    ```
**Possible values in cds:**
```
  Code a: ['DVD video', 'U-matic', 'streaming video', 'Streaming video', 'U-Matic SP', 'DVD', 'Betacam SP', 'U-Matic', 'Betacam', 'VHS', '... +4 more values']
  Code c: ['19970709', '19970627']
  Code b: ['CARBONI-1', 'AWABATA', 'Master', 'RAICH-1', 'RAICH-3', 'RAICH-2', 'RAICH-4']
  Code d: ['', 'PAL']
  Code k: ['19830121', '19950509', '19950508', '19830128', '19991122', '19991123', '19941103', '19941102', '19991126', '20000414', '... +718 more values']
  Code j: ['Master', 'Maste']
  Code 2: ['CERN-VIDEO-C-133-C', 'CERN-VIDEO-C-133-B', 'CERN-VIDEO-C-133-A', 'CERN-VIDEO-C-133-F', 'CERN-VIDEO-C-133-E', 'CERN-VIDEO-C-133-D']
  Code t: ['1']
  Code 9: ['RUBBIA', 'PERLMUTTER', 'DI LELLA-4', 'DI LELLA-5', 'DI LELLA-2', 'DI LELLA-3', 'NICOLAI-1', 'DI LELLA-1', 'CARPENTER-3', 'PERINI-2', '... +751 more values']
  Code 8: ['CERN-VIDEO-C-41-D', 'CERN-VIDEO-C-41-A', 'CERN-VIDEO-C-41-B', 'CERN-VIDEO-C-41-C', 'V', 'AB', 'JANOT', 'WILSON-3', 'C2', 'NOBEL 84', '... +34 more values']
  Code J: ['Master']
```
Example [record1](https://cds.cern.ch/record/423852) [record2](https://cds.cern.ch/record/254588)
```xml=
<datafield tag="340" ind1=" " ind2=" ">
    <subfield code="a">Streaming video</subfield>
</datafield>

<datafield tag="340" ind1=" " ind2=" ">
    <subfield code="8">A</subfield>
    <subfield code="9">CATANI-1</subfield>
    <subfield code="a">Betacam</subfield>
    <subfield code="j">Master</subfield>
    <subfield code="k">19981123</subfield>
</datafield>

<datafield tag="340" ind1=" " ind2=" ">
    <subfield code="a">paper</subfield>
</datafield>
```

### ✅ 240 Tag 

**DECISION:** Drop it

[example](https://cds.cern.ch/record/351126)
```xml=
<datafield tag="240" ind1=" " ind2=" ">
    <subfield code="a">Streaming video</subfield>
</datafield>
```

### ✅ 337 Tag?

**DECISION:** Check the values, if only video, drop it. Checked and looks like we only have `Video`.

[example](https://cds.cern.ch/record/332604)
```xml=
<datafield tag="337" ind1=" " ind2=" ">
    <subfield code="a">Video</subfield>
</datafield>
```


### ✅❓ 035 Tag 

**DECISION:** Check how many, will be alternative identifiers. Checked, we have a lot(+1k).

* `035` SYSTEM CONTROL NUMBER
    * $a   System control number (NR) - [CER,IEX,MAN,MMD,WAI/UDC]
    * $9   System control number: Inst. (NR) - [CER,"CERN annual report", "CERN ISOLDE",IEX,MAN,MMD,WAI/UDC]
    * NOTE: 035 $9 inspire {record with other subject than Particle Physics to import into INSPIRE}

**Possible values in cds:**  
```
Code a: ['a032636c1', 'a032636c0', 'a057972', 'a057973', 'a057976', 'a057974', 'a057975', 'a063355', 'a063354', 'a063357', '... +1739 more values']
Code 9: ['Indico', 'Agendamaker', 'AgendaMaker', 'CERCER', 'CERN annual report']
```

[Example1](https://cds.cern.ch/record/43728) [example2](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="035" ind1=" " ind2=" ">
    <subfield code="9">PHOPHO</subfield>
    <subfield code="a">0005198</subfield>
</datafield>

<datafield tag="035" ind1=" " ind2=" ">
    <subfield code="a">0171261CERCER</subfield>
</datafield>
```

### ✅ 595, 594, 597 Tag

**DECISION:** Add to curation field.

* `594` TYPE OF DOCUMENT
    * $a   Type of document (NR) - [ARDA]

* `595` INTERNAL NOTE 
    * $a   Internal note (NR) - [ARC,CER,IEX,MAN,MMD]
    * $d   Control field (NR)
    * $i   INSPEC number
    * $s   Subject note (NR) - [MMD]

* `597` OBSERVATION IN FRENCH
    * $a   Observation in French (NR) - [MMD]
    
[Example](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="595" ind1=" " ind2=" ">
    <subfield code="a">VIDEO-MF</subfield>
</datafield>
```
```xml=
<datafield tag="594" ind1=" " ind2=" ">
<subfield code="9">review</subfield>
<subfield code="a">Conference Speech</subfield>
</datafield>
<datafield tag="595" ind1=" " ind2=" ">
<subfield code="a">VHS video</subfield>
</datafield>
<datafield tag="597" ind1=" " ind2=" ">
<subfield code="9">review</subfield>
<subfield code="8">e</subfield>
<subfield code="a">Fin conference 1:12:55</subfield>
</datafield>
```
- [example](https://cds.cern.ch/record/2001079)
    ```xml=
    <datafield tag="595" ind1=" " ind2=" ">
        <subfield code="a">Press</subfield>
        <subfield code="s">Press Videos</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/320122)
    ```xml=
    <datafield tag="595" ind1=" " ind2=" ">
        <subfield code="z">UNCL</subfield>
    </datafield>
    <datafield tag="595" ind1=" " ind2=" ">
        <subfield code="a">expedition-2019 Library collection</subfield>
    </datafield>
    <datafield tag="595" ind1=" " ind2=" ">
        <subfield code="a">Expedition-2019: 1 VHS</subfield>
    </datafield>
    ```

### ✅❓ 916 Tag

**DECISION:** TO check with Jean-Yves

* `916 "STATUS WEEK"
    * $a   Acquisition of proceedings code (NR) - [CER]
    * $d   Display period for books (NR) - [CER]
    * $e   Number of copies bought by CERN (ebooks) - [CER]
    * $s   Status of record (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
    * $w   Status week (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
    * $y   Year for Annual list (NR) - [CER]

- [example](https://cds.cern.ch/record/423917/export/xm?ln=en)
    ```xml=
    <datafield tag="916" ind1=" " ind2=" ">
    <subfield code="a">1</subfield>
    <subfield code="s">r</subfield>
    <subfield code="w">200107</subfield>
    <subfield code="y">y2005</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/254588/)
    ```xml=
    <datafield tag="916" ind1=" " ind2=" ">
        <subfield code="s">n</subfield>
        <subfield code="w">199335</subfield>
    </datafield>
    ```
- [example](https://cds.cern.ch/record/1016352)
    ```xml=
    <datafield tag="916" ind1=" " ind2=" ">
        <subfield code="d">200703</subfield>
        <subfield code="s">h</subfield>
        <subfield code="w">200707</subfield>
    </datafield>
    ```

### ✅❓ 961, 963 and 964 Tag

#### ❓ 961 Tag
**DECISION:** Check with Jean-Yves
* `961` CAT (R) [Invenio/MySQL]
    * [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) 
        * $a Cataloguer (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
        * $b Cataloguer level (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
        * $c Modification date (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
        * $l Library (NR) - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
        * $h Hour - (NR) [ARC,CER,IEX,MAN,MMD,WAI/UDC]
        * $x Creation date(NR)  - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
    - [CDS MARC21:](https://gitlab.cern.ch/webcast/micala/blob/master/helpers/xml.py#L353)
        - tag 961, subfield code x for creation date
        - tag 961, subfield code c for 
    - [From Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L98)
    ```xml=
    <datafield tag="961" ind1=" " ind2=" ">
        <!--
        <subfield code="x">2014-02-10T11:50:49</subfield>
        <subfield code="c">2014-02-19T15:25:05</subfield>
        -->
    </datafield>
    ```
#### ✅❓ 963 TAG
**DECISION:** Check, Drop it  
possible values in cds:
```
  Code a: ['RESTRICTED', 'PUBLIC']
  Code 9: ['review\n', 'review']
  Code 8: ['a', 'c', 'b', 'e', 'd', 'g', '1']
```
* `963` OWNER (NR) [Invenio/MySQL]
    * [How to MARC:](https://cds.cern.ch/help/admin/howto-marc?ln=en) 
        * $a Owner - [ARC,CER,IEX,MAN,MMD,WAI/UDC]
    - [From Old Indico to CDS:](https://gitlab.cern.ch/webcast/micala/blob/master/cds_record_origin.xml#L104) (new one does not have this as hardcoded)
    ```xml=
    <datafield tag="963" ind1=" " ind2=" ">
        <!-- HARDCODED -->
        <subfield code="a">PUBLIC</subfield>
    </datafield>
    ```    
#### ❓ 964 TAG

**DECISION:** Check with Jean-Yves

* `964`   ITEM (NR) [Invenio/MySQL]
    * Indicates the number of physical items attached to the record. The field is created as soon as an item is linked to the record.
    * $a Owner - [ARC,CER,IEX,MAN,MMD,WAI/UDC]

[example](https://cds.cern.ch/record/254588/)
```xml=
<datafield tag="961" ind1=" " ind2=" ">
    <subfield code="c">20070607</subfield>
    <subfield code="h">2046</subfield>
    <subfield code="l">CER01</subfield>
    <subfield code="x">19931028</subfield>
</datafield>

<datafield tag="964" ind1=" " ind2=" ">
    <subfield code="a">0004</subfield>
</datafield>

<datafield tag="963" ind1=" " ind2=" ">
    <subfield code="a">PUBLIC</subfield>
</datafield>
```

 
### ✅❓ 981 Tag
    
**DECISION:** Check with Jean-Yves

* `981`   SYSTEM NUMBER OF DELETED DOUBLE RECORDS 
    * $a   System number (NR) - [ARC,CER,IEX,MAN,MMD,WAI]

[example](https://cds.cern.ch/record/422936)
```xml=
<datafield tag="981" ind1=" " ind2=" ">
    <subfield code="a">002170799CER01000422935 001 422935</subfield>
</datafield>
```

### ✅❓ 306 Tag

**DECISION:** Check with Jean-Yves

[example](https://cds.cern.ch/record/2276119)
```xml=
<datafield tag="306" ind1=" " ind2=" ">
    <subfield code="a">000421</subfield>
</datafield>
```

### ✅❓ 901 Tag
**DECISION:** Check with Jean-Yves
* `901`   AFFILIATION AT CONVERSION AL300/AL500  (R) [CERN]
    * $u   Name of institute (NR) - [CER,MAN] {Now no more in use for CER, but 100 $u and 700 $u}
    
[example](https://cds.cern.ch/record/349042/)
```xml=
<datafield tag="901" ind1=" " ind2=" ">
    <subfield code="u">LBL</subfield>
</datafield>
```

### ✅ 111 Tag
- From indico:
    - a for title
    - c for location name and room
    - 9 for startDate
    - z for endDate
    - g for event ID
    
- `111`   MAIN ENTRY--MEETING NAME  (NR) [CERN]
    * $a   Meeting: conference, school, workshop (NR) - [CER,MAN]
    * $c   Location of meeting  (NR) - [CER]
    * $d   Date of meeting (NR) - [CER]
    * $f   Year of meeting (NR) - [CER]
    * $g   Conference code (NR) - [CER]
    * $n   Number of part/section/meeting (NR) - [CER]
    * $w   Country code (NR) - [CER]
    * $z   Closing date (NR) - [CER]
    * $9   Opening date (NR) - [CER]

- Proposed solution, DECISION:
    - I think we can try to get the details from `111` first, like date, location, title and event id than other fields?
    
- Not all records has this
```xml=
<datafield tag="111" ind1=" " ind2=" ">
    <subfield code="a">Holography and Regge Phases at Large U(1) Charge</subfield>
    <subfield code="c">CERN - 4/3-006 - TH Conference Room</subfield>
    <subfield code="9">2024-11-19T14:00:00</subfield>
    <subfield code="z">2024-11-19T16:00:00</subfield>
    <subfield code="g">1447077</subfield>
</datafield>
```
### ✅❓ 336 Tag
    
**DECISION:** Check with Jean-Yves

* `336` Content Type (R)
    * $a   Content type term (R) - [CER]
    * NOTE: use for SLIDES

[example](https://cds.cern.ch/record/422919/export/xm?ln=en)
```xml=
<datafield tag="336" ind1=" " ind2=" ">
<subfield code="a">Multiple videos have been identified with recid: 422919</subfield>
</datafield>
```


### ✅❓ 583 Tag

**DECISION:** Check with Jean-Yves

* `583__` ACTION NOTE  (R) [CERN]
    * $a   Action  (NR) - [CERN:BOOKSHOP,MAN]
    * $c   Time/date of action  (NR) - [CERN:BOOKSHOP,MAN]
    * $i   Mail; Method of action (NR) - [MAN]
    * $z   Note (NR) - [CERN:ALD] 

[example](https://cds.cern.ch/record/422919/export/xm?ln=en)
```xml=
<datafield tag="583" ind1=" " ind2=" ">
    <subfield code="a">curation</subfield>
    <subfield code="c">Decembre 2020</subfield>
    <subfield code="z"> -Audio: TRUE -Video Signal: TRUE -Multiple: FALSE -Relevant to CERN: TRUE -Action required: To be added (files) -Duplicate: TRUE</subfield>
</datafield>
```


## Missing from Indico Metadata

### ✅ Location (Decision: Keep the location)

- Some records in current CDS also keeps the location value but they're not in the same format. Do we need it?


## Exceptional 

- This [record](https://cds.cern.ch/record/281782)(it's not a digitized record) has multiple videos and they're not displaying 

- These digital memory records has one video, where should we include?
    - https://cds.cern.ch/record/423086
    - https://cds.cern.ch/record/359337

- Some records don’t have videos (in lecture & events collection), they have pdf 
    - https://cds.cern.ch/record/1359176
    - https://cds.cern.ch/record/1359188
    - https://cds.cern.ch/record/1359179

- Some of them don’t have videos or pdf
    - https://cds.cern.ch/record/407778
    - https://cds.cern.ch/record/533403

- These records has the lecturemedia videos but they're not displaying
    - https://cds.cern.ch/record/349043
    - https://cds.cern.ch/record/281782
    - https://cds.cern.ch/record/320122
    - https://cds.cern.ch/record/349046
    - https://cds.cern.ch/record/423084

- Digital Memory records? example:
    - https://cds.cern.ch/record/533641
    - https://cds.cern.ch/record/319577
    - https://cds.cern.ch/record/319578
    - https://cds.cern.ch/record/328990

