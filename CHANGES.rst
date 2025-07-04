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
