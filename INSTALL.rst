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

**Build the docker image**:

.. code-block:: console

    $ docker-compose build

Since we are mounting current directory as a volume, the CDS package inside the docker container will be overwritten with the content of the current directory. We need to **install the CDS package** outside of docker:

.. code-block:: console

    $ workon cds3 # This is not necessary, but installing packages inside virtualenv is always recommended
    (cds3)$ pip install -e . # This should create `CDS.egg-info` directory

Now, we can **start docker container**:

.. code-block:: console

    $ docker-compose up

To stop docker use `Ctrl+C`. If something bad happens and containers are not stopped correctly, you can stop all running containers with the following command:

.. code-block:: console

    $ docker stop $(docker ps -a -q)


To **create database & user** you can use one of two different ways:

* Open a bash session in a running container and execute commands there:

.. code-block:: console

    $ docker ps # list the running containers. Copy the name of the web container, something like cds3_web_1
    $ docker exec -it cds3_web_1 bash # where cds3_web_1 is the name of the container from the previous step
    cds@1b83f7ba9a3c:/code$ cds db init
    cds@1b83f7ba9a3c:/code$ cds db create
    cds@1b83f7ba9a3c:/code$ cds users create test@test.ch -a

* or send commands directly to the docker container:

.. code-block:: console

    $ docker exec -it cds3_web_1 cds db init
    $ docker exec -it cds3_web_1 cds db create
    $ docker exec -it cds3_web_1 cds users create test@test.ch -a


**Create a record**. This can be done again inside a web container, following the instruction from the **Manual** paragraph, but the following command can be executed outside of a docker container (plus it's a good example of how to send a pipe instruction to docker container):

.. code-block:: console

    $ docker exec cds3_web_1 sh -c "echo '{\"title\":\"Invenio 3 Rocks\", \"recid\": 1}' | cds records create"


**Create a PID for the record**

.. code-block:: console

    $ docker exec -it cds3_web_1 cds shell

.. code-block:: python

    from invenio_db import db
    from invenio_pidstore.models import PersistentIdentifier
    pid = PersistentIdentifier.create('recid', '1', 'recid')
    pid.assign('rec', '1')
    pid.register()
    db.session.commit()
