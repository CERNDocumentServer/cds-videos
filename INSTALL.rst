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
    (cds3)$ pip install -e .[all]

Build the assets

.. code-block:: console

    (cds3)$ cds bower
    (cds3)$ cdvirtualenv var/cds-instance
    (cds3)$ bower install
    (cds3)$ cds collect -v
    (cds3)$ cds assets build

Create database & user

.. code-block:: console

    (cds3)$ cdvirtualenv src/cds
    (cds3)$ honcho start
    (cds3)$ cds db init
    (cds3)$ cds db create
    (cds3)$ cds users create -e test@test.ch -a

Create a record

.. code-block:: console

    (cds3)$ echo '{"title":"Invenio 3 Rocks", "recid": 1}'  | cds records create

Create a PID for the record

.. code-block:: console

    (cds3)$ python manage.py shell

.. code-block:: python

    from invenio_db import db
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.create('recid', '1', 'recid')
    pid.assign('rec', '1')
    pid.register()
    db.session.commit()

Now you can visit http://localhost:5000/records/1 and see your record :)

Docker
------

Soon ...
