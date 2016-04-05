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
    (cds3)$ pip install -e .[postgresql]
    (cds3)$ python -O -m compileall .

Build the assets

.. code-block:: console

    (cds3)$ cds npm
    (cds3)$ cdvirtualenv var/instance/static
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
    (cds3)$ cds users create test@test.ch -a
    (cds3)$ cds index init


Create a record

.. code-block:: console

    (cds3)$ cds fixtures invenio

Or you can create the entire CDS Theses collection ~ 10 mins

.. code-block:: console

    (cds3)$ cds fixtures cds

Create some demo files

.. code-block:: console

    (cds3)$ cds fixtures files

Run example development server:

.. code-block:: console

    $ cds --debug run

Now you can visit http://localhost:5000/ :)

Docker
------

Soon ...
