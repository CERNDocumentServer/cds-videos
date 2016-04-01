Installation
============

Manual
------

Prepare the environment

.. code-block:: console

    $ npm install -g node-sass clean-css requirejs uglify-js
    $ mkvirtualenv cds3
    (cds3)$ cdvirtualenv ; mkdir src ; cd src
    (cds3)$ git clone -b cdslabs_qa git@github.com:CERNDocumentServer/cds.git
    (cds3)$ cd cds
    (cds3)$ pip install -r requirements.txt

Build the assets

.. code-block:: console

    (cds3)$ cds npm
    (cds3)$ cdvirtualenv var/cds-instance/static
    (cds3)$ npm install
    (cds3)$ cds collect -v
    (cds3)$ cds assets build

Make sure that ``elasticsearch`` server is running:

.. code-block:: console

    $ elasticsearch
    ... version[2.0.0] ...

Create database & user

.. code-block:: console

    (cds3)$ cdvirtualenv src/cds
    (cds3)$ cds db init
    (cds3)$ cds db create
    (cds3)$ cds users create -e test@test.ch -a
    (cds3)$ cds index init


Create a record

.. code-block:: console

    (cds3)$ cds fixtures invenio

Or you can create the entire CDS Theses collection ~ 10 mins

.. code-block:: console

    (cds3)$ cds fixtures cds

Run example development server:

.. code-block:: console

    $ flask -a app.py --debug run

Now you can visit http://localhost:5000/ :)

Docker
------

Soon ...
