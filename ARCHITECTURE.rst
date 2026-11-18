..
    This file is part of CDS.
    Copyright (C) 2026 CERN.

    CDS is free software; you can redistribute it
    and/or modify it under the terms of the GNU General Public License as
    published by the Free Software Foundation; either version 2 of the
    License, or (at your option) any later version.

Frontend architecture
=====================

This document describes how the user interface of CDS Videos is built and
the conventions of its code. The setup and the REST API are described in
``README.rst``.

.. contents::
   :local:
   :depth: 2

Overview
--------

CDS Videos is not a single page application. Flask renders every page with
Jinja, and React renders the interactive parts of a page, the way the
AngularJS directives did before:

1. A view renders a Jinja template of the ``semantic-ui`` theme
   (``APP_THEME = ["semantic-ui"]``). The template contains mount points
   carrying their settings as ``data-*`` attributes, and sometimes the
   record itself as embedded JSON.
2. The template includes one webpack entry (``{{ webpack['cds_records_app.js'] }}``).
   The entry finds its mount points and renders a React tree in each of
   them with ``createRoot``.
3. The React components read and write through the REST API (``/api``)
   with the shared HTTP client.

The stack:

* React 18, PropTypes, Semantic UI React 3 and the Semantic UI LESS theme
* react-searchkit 4 for every list of results (search page, home page
  widgets, related videos, list of uploads)
* Redux with thunks and Formik for the deposit form
* axios for HTTP, lodash, clsx, DOMPurify, HugeRTE for the rich text editor
* rspack (through Invenio-Assets) to bundle, pnpm to install

Where things live
-----------------

::

    cds/modules/theme/
        webpack.py                 entries, JavaScript dependencies, aliases
        assets/semantic-ui/
            js/cds/
                entries/           one file per webpack entry, mounts only
                shared/            HTTP client, DOM helpers, utils, generic components
                header/            header search bar, navbar, announcement
                search/            react-searchkit app, results, facets, widgets
                record/            record pages (project/, video/, components/)
                deposit/           upload form and list of uploads
            less/
                theme.config       Semantic UI theme configuration
                site/              Semantic UI site overrides
                cds/               CDS styles (cds.less is the bundle)
                cds_previewer/     styles of the video player page
                cds_records/       styles of the record statistics
                cds_admin/         Bootstrap rules for the Invenio-Admin panel
    cds/modules/<module>/templates/semantic-ui/<module>/
                                   Jinja templates of each module

Webpack entries
~~~~~~~~~~~~~~~

All entries are declared in ``cds/modules/theme/webpack.py``.

============================== ============================ ==========================================
Entry                          Source                       Pages
============================== ============================ ==========================================
``cds_theme_app``              ``entries/theme.js``         every page: header, navbar, announcement
``cds_search_ui_app``          ``entries/search.js``        search page, home page widgets
``cds_records_app``            ``entries/record.js``        video and project pages
``cds_records_stats_app``      ``entries/recordStats.js``   statistics of a record
``cds_deposit_app``            ``entries/deposit.js``       upload form and list of uploads
``cds_theme_styles``           ``less/cds/cds.less``        every page
``cds_previewer_styles``       ``less/cds_previewer``       video player (also embedded)
``cds_records_stats_styles``   ``less/cds_records``         statistics of a record
``cds_admin_styles``           ``less/cds_admin``           Invenio-Admin panel
============================== ============================ ==========================================

An entry only mounts: it reads the settings of its mount points and
renders a component of a feature folder. It holds no logic of its own.

From the page to React
----------------------

Settings
~~~~~~~~

The template passes the settings of a mount point as ``data-*``
attributes (URLs of the API, flags such as ``data-is-super-admin``, the
email of the current user). The entry reads ``element.dataset`` and
passes them as props. Keep the attribute names in kebab case in the
template and read them in camel case in JavaScript.

Embedded records
~~~~~~~~~~~~~~~~

To render without waiting for a request, two pages embed the record as
the REST API returns it, with the same permission check and serializer:

* the record page embeds ``GET /api/record/<recid>`` in
  ``#cds-record-json`` (``cds.modules.records.views.serialize_record``)
* the edit page of a project embeds ``GET /api/deposits/project/<pid>`` in
  ``#cds-deposit-project``

Nothing is embedded for the users who cannot read the record: the page
then fetches it and gets the error of the API. Read embedded JSON with
``parseJSON`` from ``shared/dom.js``.

HTTP
~~~~

Use ``http`` from ``shared/api.js`` for every request, never ``fetch`` or
a new axios instance:

* it adds the ``X-CSRFToken`` header to unsafe requests (the REST API
  checks it)
* it counts the pending requests for the loading bar of the search pages.
  Pass ``ignoreLoadingBar: true`` in the request config for background
  requests (polling, refreshes, uploads)

The deposit API answers ``304`` while the revision of a record is
unchanged, although the task states it returns change without a new
revision. Requests that must see the live state use
``NO_CACHE_HEADERS`` of ``deposit/api.js``.

Features
--------

Search (``search/``)
~~~~~~~~~~~~~~~~~~~~

``search/mount.js`` mounts one react-searchkit app for the element carrying
the ``data-search-*`` attributes, like ``<invenio-search>`` did. The page
rendered by Jinja holds placeholders (``[data-cds-search-component]``) in
its header, facets and results columns, and each one becomes a React
portal of that app, so they share one search state.

The home page widgets, the related videos of a record and the list of
uploads are searches too, with their own result templates
(``search/components/VideoTemplates.js``, ``deposit/list/``).

Record pages (``record/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~

``RecordView`` takes the embedded record (or fetches it) and renders the
project or the video page. The video page is a container,
``video/VideoDetail.js``, which holds the state (player time, selected
transcript, expanded description) and passes everything to sections
(``VideoHeader``, ``VideoPlayerSection``, ``VideoDescription``,
``DescriptionDetails``) that take props and have no hooks.

Deposit (``deposit/``)
~~~~~~~~~~~~~~~~~~~~~~

The upload form is the only part with application state, kept in a Redux
store created per page (``deposit/state/store.js``):

* ``state/reducer.js``: the page and one immutable entry per deposit
  (project and videos), with its record, status and errors
* ``state/records.js``: pure helpers on records (status, master file,
  defaults, inherited metadata)
* thunks for the side effects: ``actions.js`` (save, publish, delete),
  ``deposit.js`` (changes of a record: values, access, errors),
  ``tasks.js`` (polling of the workflow), ``permissions.js``,
  ``uploads.js``, ``page.js`` (page setup)
* the requests changing deposits go through a queue
  (``thunk.withExtraArgument({ queue })``), so a save always sends the
  latest record and two saves never overlap
* ``state/registry.js`` keeps what is not rendered (registered fields,
  files waiting for upload, extracted metadata in the local storage)
* components take a deposit ``id`` and read the store with the hooks of
  ``state/hooks.js`` (``useDeposit``, ``useDepositActions``)

Each project and video panel is a Formik form (``fields/DepositForm.js``).
The fields write to the record in the store, and the form follows the
changes made by the page (``formSync``) or is reset to the record
(``formReset``). Client side validation is in ``fields/validation.js``,
the errors of the server are shown on the fields that are rendered.

Category access
^^^^^^^^^^^^^^^

Categories are records with their own ``_access.read``: a user only gets
the categories of their e-groups from ``/api/categories/`` (all categories
for super admins, only ``OPEN`` in the fixtures for the others). The form
reads the access rules of the category of a project (``public``,
``restricted``, ``responsible``) from that list. An editor who cannot read
the category of a project can edit it but not change its restrictions.

Access of records
~~~~~~~~~~~~~~~~~

The record serializer gives everyone ``_access.status`` (``public`` or
``restricted``). Only the users who can edit a record get who can read
and edit it (``_access.read`` and ``_access.update``). Use ``isPublic``
of ``shared/utils/records.js`` to label a record, never the lists.

Styles
------

* Semantic UI is built from LESS by Invenio-Theme with the configuration
  of ``less/theme.config`` and the overrides of ``less/site``.
* The CDS styles are LESS too (``less/cds``), with the classes of the
  previous theme: the ``cds-`` layout and grid (``cds-row``,
  ``cds-col-sm-6``, ``cds-panel``) and the utilities (spacing such as
  ``mt-20`` or ``px-10``, colors, decorators). Prefer a Semantic UI
  component or a utility class to a new rule.
* Font Awesome 4 is still used for the icons of the previous interface,
  next to the Semantic UI icons.
* The Invenio-Admin panel (``/admin``) is written for Bootstrap 3, which
  the theme does not load: ``less/cds_admin`` adds the few Bootstrap rules
  it needs.

Build
-----

Dependencies
~~~~~~~~~~~~

The JavaScript dependencies are declared in ``webpack.py`` (and in the
bundles of the installed Invenio modules). ``cds webpack create``
generates a ``package.json`` from them, which is committed with its
``pnpm-lock.yaml`` at the root of the repository.

* ``./scripts/build-assets`` fails when the generated ``package.json``
  differs from the committed one, then installs with
  ``pnpm install --frozen-lockfile`` and builds with rspack.
* After changing a dependency (in ``webpack.py`` or by upgrading an
  Invenio module), run ``./scripts/lock-assets`` and commit both files.
  It starts from the current lock file, so the other packages keep their
  versions.
* ``./scripts/assets-watch`` rebuilds on every change during development.

rspack
~~~~~~

The bundles are built with the rspack project of Invenio-Assets 4
(``WEBPACKEXT_PROJECT``), which needs Node.js 20.19 or later (CI and the
Docker image use Node.js 24). webpack is still available with
``WEBPACKEXT_PROJECT = "invenio_assets.webpack:project"``.

Aliases (``webpack.py``):

* ``@js/cds`` and ``@less/cds`` for imports across features
* ``react-searchkit`` resolves to its ES modules build, so axios is bundled
  once and semantic-ui-react can be tree shaken

Large libraries load when they are first needed, with a dynamic
``import()``: d3 with the year facet of the search page, HugeRTE with the
first rich text field of the deposit form. Keep new heavy dependencies
out of the entries the same way.

Conventions
-----------

Code
~~~~

* Function components and hooks only. Default values are default
  parameters, not ``defaultProps`` (removed in React 19), and every
  component declares its ``propTypes``.
* One component, or one topic for helpers, per file. Name the file after
  its main export.
* Imports use relative paths within a feature and ``@js/cds/...`` across
  features. Features import from ``shared/``, and from ``search/`` for its
  mount helpers and widgets. Other imports between features are a sign
  that the code belongs in ``shared/``.
* ``async`` and ``await`` instead of chains of ``then``.
* Render what is shown with ``{condition && ...}``. Hide with
  ``display: none`` only when unmounting would lose state (a player
  iframe, an editor, the open tab), and say why in a comment.
* Class names with ``clsx``.
* HTML from the server: ``TrustedHtml`` (``record/components``) for record
  fields the server already sanitized, ``SanitizedHtml``
  (``deposit/components``) to sanitize with DOMPurify before rendering.
* Loading states use Semantic UI placeholders shaped like the content
  (``search/components/Placeholders.js``, ``deposit/DepositFormPlaceholder.js``),
  not spinners.
* Keep the CSS classes and the texts of the previous interface where the
  end to end tests or the users rely on them.
* Format with Prettier, with ``--trailing-comma es5``.

Templates
~~~~~~~~~

* A template only lays out the page and passes data. Logic belongs to the
  view or to the React component.
* Templates live in ``templates/semantic-ui/<module>/`` of their module.

Tests
-----

The user interface is tested end to end with Playwright in ``tests/e2e``
(see its ``README.md``). The specs locate elements as a user does (roles,
labels, texts), compare the page with the REST API instead of hard coding
records, and fail on uncaught page errors. The same specs can run against
two interfaces (projects ``angularjs`` and ``react``), which is how the
React port was compared with the AngularJS one.

When changing a page:

* add or update a spec next to the existing ones (``specs/<page>.spec.js``)
* add the records it needs to ``tests/e2e/seed.py`` and the users to
  ``tests/e2e/setup.sh``
* in CI the ``tests-e2e`` job runs the ``react`` project on Node.js 24
  and 26 and uploads the report and traces on failure

Adding a page
-------------

1. Add the view and its Jinja template in
   ``templates/semantic-ui/<module>/``, with a mount point carrying its
   settings as ``data-*`` attributes.
2. Add the components in the feature folder (or a new one under
   ``js/cds``) and an entry in ``js/cds/entries`` that mounts them.
3. Declare the entry, and any new dependency, in
   ``cds/modules/theme/webpack.py``, then run ``./scripts/lock-assets``.
4. Include the entry in the template with ``{{ webpack['<entry>.js'] }}``.
5. Add an end to end spec.
