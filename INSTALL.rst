Installation
============

Manual
------

Prepare the environment

.. code-block:: console

    $ npm install -g node-sass clean-css requirejs uglify-js
    $ mkvirtualenv cds
    $ cdvirtualenv ; mkdir src ; cd src; git clone -b cdslabs_qa git@github.com:CERNDocumentServer/cds.git ; cd cds
    $ pip install -e .[all]

Build the assets

.. code-block:: console

    $ cds bower
    $ cdvirtualenv var/cds-instance
    $ bower install
    $ cds collect -v
    $ cds assets build

Create database & user

.. code-block:: console

    $ cdvirtualenv src/cds
    $ honcho start
    $ cds db init
    $ cds db create
    $ cds users create -e test@test.ch -a

Create a record

.. code-block:: console

    $ echo '{"title":"Invenio 3 Rocks", "recid": 1}'  | cds records create

Create a PID for the record

.. code-block:: console

    $ python manage.py shell

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
