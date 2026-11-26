..
    This file is part of CDS.
    Copyright (C) 2015, 2018 CERN.

    CDS is free software; you can redistribute it
    and/or modify it under the terms of the GNU General Public License as
    published by the Free Software Foundation; either version 2 of the
    License, or (at your option) any later version.

    CDS is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CDS; if not, write to the
    Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
    MA 02111-1307, USA.

    In applying this license, CERN does not
    waive the privileges and immunities granted to it by virtue of its status
    as an Intergovernmental Organization or submit itself to any jurisdiction.


Changes
=======

Version 3.1.3 (2026-11-26)

- fix(search): run the search when a suggestion is chosen on the search page
- fix(ui): show the mobile Search button label in the page font
- fix(ui): contrast of the transcript search placeholder
- fix(admin): search box of the views with lazy column labels
- fix(player): hide the THEOplayer right click menu
- fix(ui): menu button on the right of the logo on small screens

Version 3.1.2 (2026-11-20)

- fix(ui): unencoded URLs causing errors

Version 3.1.1 (2026-11-19)

- sentry: logging still works on legacy Sentry servers with the new SDK
- global: invenio-userprofiles 7.0.4, whose user profiles migration no
  longer fails on names with an apostrophe or a colon, nor saves missing
  usernames as 'None'

Version 3.1.0 (2026-11-19)

- deposit: the contributor menu shows the format of a contributor who is
  not in the CERN directory ("Lastname, Firstname") and offers to add
  them once both names are typed, after the directory results. An empty
  contributor or licence field no longer opens on an empty line
- deposit: the searched fields (contributor name, licence) have no caret,
  only a spinner while they search
- deposit: opening a filled contributor or licence searches from its
  value, which can be edited, and a contributor keeps its role when its
  name changes

Version 3.0.1 (2026-11-18)

- deposit: the contributors search from the second character, and the
  author and licence fields show when they search (spinner and
  "Searching..." in the menu)

Version 3.0.0 (2026-11-18)

Major release: a new user interface and a new Python stack. The database
must be upgraded with ``scripts/upgrade-database`` and the assets built
with pnpm and rspack (see the upgrade notes).

Upgrade notes:

- Python 3.14, Node.js 24 (20.19 at least) and pnpm 11. The Docker image is
  built on ``ghcr.io/inveniosoftware/invenio:debian-python3.14`` and the
  instance moves from ``/opt/cds_videos`` to ``/opt/invenio``
- the Python dependencies are locked in ``uv.lock`` (``pyproject.toml``
  replaces ``setup.cfg``, ``setup.py`` and ``requirements.txt``), the
  JavaScript ones in the committed ``package.json`` and ``pnpm-lock.yaml``
- run ``scripts/upgrade-database`` once on a database of 2.x: it stamps
  two revisions alembic no longer reaches, runs ``alembic upgrade heads``
  (UTC aware datetimes, JSON to JSONB for the record history and the
  remote accounts, user profiles moved into the users table), converts
  the encrypted token columns and restores a unique index of the files.
  It cannot be reverted, back up the database first. No reindex needed.
  It stops unless the database session is in UTC: when
  ``SQLALCHEMY_ENGINE_OPTIONS`` is configured, add
  ``"connect_args": {"options": "-c timezone=UTC"}`` to it
- configuration: ``CACHE_TYPE = "RedisCache"`` (Flask-Caching 2),
  ``TRUSTED_HOSTS`` replaces ``APP_ALLOWED_HOSTS``, ``FLASK_DEBUG``
  replaces ``FLASK_ENV``
- the production image installs the ``xrootd`` extra with invenio-xrootd 3
- additional files with an extension only the MIME tables of Python 3.14
  know (``.md`` for example) are now accepted, 2.x rejected them as
  unsupported

User interface:

- ui: replace AngularJS by a React and Semantic UI interface, with the same
  pages and behaviour. The pages show from the first render (embedded
  records, placeholders while loading) and load less JavaScript and CSS
- deposit: the form state is a Redux store, saves run one at a time and
  always send the latest record (fixes the type lost when the category and
  the type were saved at once)
- deposit: publishing a video saves the project and the draft videos first
- deposit: replace CKEditor 4 (end of life) by HugeRTE for the descriptions
- deposit: a published video can be collapsed from its sticky header
- deposit: the video description explains how to write chapters
- admin: keep the static pages editor in the Invenio-Admin panel and lay it
  out with the Semantic UI theme
- ui: build the assets with rspack and install them with pnpm

Fixes:

- records: restricted records are labelled restricted for their readers.
  Everyone gets ``_access.status``, only the editors get who can read and
  edit (also for the videos embedded in a project)
- records: find the chapters in descriptions saved by the new editor, and
  link only the timestamps starting a line of a description
- records: the video links no longer load the project deposit
  (``GET /api/record/<id>`` from about 0.35 s to 0.06 s)
- records: each chapter frame is loaded once, at one size, instead of
  two or three times per record page
- deposit: fetch the project without the browser cache, so the task states
  are not reset after an upload
- deposit: reading a file with ``GET /api/deposits/<pid>/files/<key>``
  failed with a 500 (webargs 8)
- previewer: fix the subtitles of the local player and of deposit previews
- global: fix the deprecations of SQLAlchemy 2, Invenio-Records, Python 3.12
  and marshmallow 4

Dependencies:

- latest major versions of the Invenio modules, Flask 3.1, Werkzeug 3.1,
  SQLAlchemy 2.0, Flask-SQLAlchemy 3.1, React 18, semantic-ui-react 3 and
  react-searchkit 4

Tests and documentation:

- tests: Playwright end to end tests of the user interface, including who
  can see the records, the deposits and the categories
- ci: end to end tests on Node.js 24 and 26, unit tests on Python 3.14 and
  3.15 (allowed to fail)
- docs: ``ARCHITECTURE.rst`` describes the frontend architecture and
  conventions

Version 2.15.0 (2026-10-29)

- feat(files): add support for EOS storage offloading
- feat(collections): hide multiple collection facet values and keep only the selected one

Version 2.14.0 (2026-10-26)

- migrate statistics to yearly indices

Version 2.13.3 (2026-09-28)

- fix(ui): encode keyword names in search links

Version 2.13.2 (2026-08-04)

- tests(serializer): ensure internal fields are removed
- fix(serializer): remove unnecessary fields for non-permitted users
- fix(setup): incorrect expose for docker compose OS dashboard

Version 2.13.1 (2026-05-29)

- legacy: add new route to resolve legacy file links
- fix(ui): wrap long related identifiers

Version 2.13.0 (2026-04-22)

- facets: add collection facet
- fix(frames): correct extracted frame timestamp calculation
- fix(ldap):add exact e-group mail match
- deposit: preserve legacy_recid and _curation fields
- sanitizer: allow href and link in ckeditor
- fix(permissions): allow update users to read metadata/files

Version 2.12.0 (2026-04-08)

- schema: normalize MARC tag keys to numeric format in serializer
- schema: add new curation fields for digitized videos
- requirements: bump invenio-files-rest to allow range requests

Version 2.11.1 (2026-03-17)

- fix(serializer): include hours in VTT timestamp formatting

Version 2.11.0 (2026-02-17)

- player: add keyboard shortcuts
- ui: always display edit and publish buttons
- fix(serializer): do not remove HTML tags for titles

Version 2.10.1 (2026-01-28)

- fix(keywords): syntax error on escape double quotes on keyword name

Version 2.10.0 (2026-01-28)

- fix(keywords): escape double quotes on keyword name
- fix(stats): remove double variable assignment
- requirements: bump counter-robots lib
- subtitles: support srt files and convert to vtt

Version 2.9.2 (2025-11-28)

- deposit: add CKEditor `Source` back and sanitize HTML using DOMPurify
- dependencies: add DOMPurify (MPL-2.0) for HTML sanitization
- sanitizer: allow style attribute for description

Version 2.9.1 (2025-11-20)

- downloads: re-added thumbnails section with chapter frames filtered out

Version 2.9.0 (2025-11-18)

- stats: add fields for migration
- share: set start time from current player position
- fix(in-this-video-section): align title and top line

Version 2.8.1 (2025-11-05)

- fix(search): restrict searches to pre-defined fields
- fix(keywords): overlapping on render
- fix(player): menu for subtitles


Version 2.8.0 (2025-11-05)

- Add `autogenerated` for subtitles to be displayed in the editor.

Version 2.7.0 (2025-11-05)

- Add `related_identifiers`, `LECTURES` category.

Version 2.6.0 (2025-10-01)

- Introduce video chapters for users to better describe key moments of their uploaded videos
- Introduce transcription searching and automatic follow-through when users upload subtitles to their videos
- Introduce the possibility for users to upload additional video files alongside the main video.
- Introduce sharing of a video from a specific point in time.
- Allow non-CERN accounts to login to the platform so that restricted video can be shared with them. However, uploading content is still limited to CERN users only.

Version 2.5.4 (2025-09-01)

- Fix handling of ``_access.update`` to correctly append the current user.  
- Override ``bytesToHumanReadable`` to display units as KB, MB, GB, TB.  
- Add ``marshmallow_utils`` and sanitize metadata fields to remove unsafe HTML.  

Version 2.5.3 (2025-06-12)

- keywords: add missing source field used in old migrated records
- contrib: fix CERN contrib login with token

Version 2.5.2 (2025-04-02)

- stats: return generic message when stat event not valid
- requirements: Pin wtforms to 2.3.3 to be compatible with flask-admin

Version 2.5.1 (2024-12-17)

- Fix an issue with who can access to projects
- Fix description field UI when editing projects
- Fix an issue with fetching e-groups on login

Version 2.5.0 (2024-11-27)

- make DOI optional and add CLI command for DOI minting
- setup: upgrade celery and other dependencies

Version 2.4.0 (2024-11-18)

- loaders: ignore old user email when present
- doi: update datacite to v4

Version 2.3.0 (2024-11-08)

- embed: add 2 new options skin and socialSharing to control the play button icon and
  social sharing controls accordingly

Version 2.2.0 (2024-10-29)

- faq: add link anchors to each section
- trackingcode: add configuration for MATOMO

Version 2.1.5 (2024-09-25)

- deposit: add tips and suggestion on how to add a cover for an uploaded video

Version 2.1.4 (2024-09-13)

- deposit: fix publish on the first time by removing syncing of buckets and only rely on
  snapshot of the bucket

Version 2.1.3 (2024-08-14)

- flows: fix task revoke call
- deposit: fix delete video button disable condition

Version 2.1.2 (2024-08-12)

- stats: configure celery beat

Version 2.1.1 (2024-08-12)

- disable remote upload

Version 2.1.0 (2024-08-07)

- deposit: allow users to input date apart from using the datepicker
- deposit: add comma as keyword separator
- contributors: capitalize user input on suggestions
- contributors: add role 'Subtitles by'
- fix thumbnail preview
- previewer: add subtitles for local video player and fix bundles
- config: fix sorting by title on published records

Version 2.0.0 (2024-08-05)

- Move docker image to alma
- Bump python version to 3.9
- Migrate to Opensearch v2
- Migrate to webpack theme building
- Remove dependency to invenio-deposit. The necessary files have been move on its own folder
- Copy ckeditor files inside modules
- Copy bootstrap-decorator file inside modules
- Integrate invenio-stats
- Bump invenio-xrootd version
- Allow searching of contributors roles and ids in non specifying field queries
- Use files sync in both publish new and edit videos.
- Re-enable remote upload of videos by providing a downloadable link
- Remove dropbox integration from codebase

Version 1.0.44 (2024-06-28)

- Fix celery task

Version 1.0.43 (2024-06-27)

- Update FAQ
- Add config variable for shared video files
- Fix failing tests

Version 1.0.42 (2024-01-15)

- Migrate license of THEOPlayer from SDK to key
- Show video file size warning when more than 100 Mb
- Fix failing tests

Version 1.0.41 (2023-06-13)

- Fix incompatibility with Chrome popover APIs
- Conditionally show file size warning when downloading
- Improve installation documentation

Version 1.0.40 (2023-05-04)

- Fix wrong token scope for CERN SSO.

Version 1.0.39 (2023-03-22)

- Fix transcoding integration: process only one completed transcoding
  task at the same time.

Version 1.0.38 (2022-12-15)

- Fix on identity refresh roles assignment

Version 1.0.37 (2022-12-06)

- Integrate cern openid
- Add fix for user groups

Version 1.0.35 (2022-07-05)

- fixes display of the e-groups in the search of the form

Version 1.0.34 (2022-06-15)

- removes file deletion when cleaning extract metadata task

Version 1.0.33 (2022-06-14)

- copy video file to process in a temporary folder and use it for
  extract metadata and frames to avoid to copy it multiple times
- fix a layout issue of thumbnails for portrait videos
- fix an exception happening when an old video do not have the
  celery_task_id field in the metadata

Version 1.0.32 (2022-05-16)

- change the preview HTML title tag with the current video title
- add an extra check to the transcoding task to avoid to download
  the same transcoded video files multiple times.

Version 1.0.31 (2022-04-27)

- update sequence_number from video schema to be a list

Version 1.0.30 (2022-04-12)

- fix bug with delete button when upload failed
- fix bucket assignment when videos were published from project
- resume necessary tests

Version 1.0.29 (2022-03-09)

- add ALICE to video categories
- pin bootstrap-sass
- upgrade invenio-previewer

Version 1.0.28 (2022-01-26)

- Fixed banner display in video details page
- Added default CSP headers and customized them for the embedded videos
- Improved error reporting on Opencast exceptions

Version 1.0.27 (2022-01-12)

- Migration to new Opencast infrastructure
- Integration of new video uploading workflow
- Gereral impovements in the UI

Version 1.0.26 (2021-12-14)

- Update lxml package due to security issue ( https://github.com/lxml/lxml/security/advisories/GHSA-55x5-fj6c-h6m8)

Version 1.0.25 (2021-12-07)

- change doi format and register url

Version 1.0.24 (2021-11-26)

- decouple recid provider from CDS

Version 1.0.23 (2021-11-19)

- remove lowercase text transformation of emails for record restriction
- update contact page
- update record statistics queries and configuration

Version 1.0.22 (2021-10-11)

- add validation when reserving non-existing report number
- fix bucket creation issue
- normalize access check values
- update version to use sdk
- pin dictdiffer to 0.8.1
- update installation docs

Version 1.0.21 (2021-07-09)

- fix start/end time when embedding videos
- remove link to detailed video stats

Version 1.0.20 (2021-04-23)

- bump cds-dojson to add CERN member states languages

Version 1.0.19 (2021-03-28)

- bump cds-dojson to add Slovenian language validation

Version 1.0.18 (2021-03-22)

- add Slovenian language
- update FAQ text

Version 1.0.17 (2021-01-27)

- bump Python packages
- improve help text for users
- adapt THEOPlayer code to new versions

Version 1.0.16 (2020-01-24)

- bump cds-sorenson version (updated infrastructure)

Version 1.0.15 (2019-10-04)

- add record deletion interface

Version 1.0.14 (2019-07-26)

- fix md5 checksum calculation for transcoded video subformats
- add missing `*` mark for the required field `description` when creating a
  project in the  upload form

Version 1.0.13 (2019-06-20)

- activate video subtitles via URL query parameter

Version 1.0.12 (2019-06-05)

- reserve report number before uploading a video

Version 1.0.11 (2019-05-22)

- resize home page video player to be smaller
- prevent browser window to be closed while uploading a file
- limit the number of videos per project via a configuration variable

Version 1.0.10 (2019-05-10)

- bug fix for Popular Videos search query

Version 1.0.9 (2019-05-08)

- add Popular Videos links on homepage

Version 1.0.8 (2019-02-05)

- fixed cron task for indexing projects deposits
- new homepage channels and Press collection
- fixed CERN OAuth login for lightweight accounts
- fixed CERN OAuth logout redirection

Version 1.0.7 (2019-01-10)

- updated dependencies, vulnerabilities removed
- search guide added
- files integrity checks disabled
- fixing deposit statuses added
- fixed invenio-opendefinition usage

Version 1.0.6 (2018-07-04)

- implemented responsive player for embed videos
- fixed keywords inheritance in the deposit

Version 1.0.5 (2018-06-22)

- replaced cds-iiif module with latest invenio-iiif package
- bumped cds-sorenson to enable small videos transcoding
- improved search ui performance

Version 1.0.4 (2018-06-13)

- added sorting options when searching
- added e-groups autocompletion for restricted videos
- added embedding configuration options

Version 1.0.3 (2018-06-06)

- added search suggestions on search page
- fixed video playback for uncommon video formats
- fixed record statistics charts
- fixed deposit indexing
- fixed UI issues with IE11
- fixed video preview image aspect ratio for some videos

Version 1.0.2 (2018-05-16)

- Invenio v1.0.0 package releases update.

Version 1.0.1 (2018-05-14)

- deposit:
  - remove SSE related code completely.
  - fixed deposit video player.
- records:
  - download box reorganization.
  - added no index for robots for projects.
  - added "Press" field until general community solution is put in place.
- security:
  - fixed file ACL check.
  - filter videos inside project according to current user provides.

(No release information until 2018-04-11)

Version 1.0.0 (2017-12-14)

- Initial release
