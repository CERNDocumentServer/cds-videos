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

Install production like setup

.. code-block:: console

    $ workon cds3
    (cds3)$ cd cds
    (cds3)$ pip install -r requirements.txt
    (cds3)$ pip install -e .

If you want to install a developer setup and use the latest versions of the
Invenio packages

.. code-block:: console

    $ workon cds3
    (cds3)$ cd cds
    (cds3)$ pip install -r requirements.developer.txt

Or to install the latest released versions of all the dependencies

.. code-block:: console

    $ workon cds3
    (cds3)$ cd cds
    (cds3)$ pip install -e .

Build the assets

.. code-block:: console

    (cds3)$ python -O -m compileall .
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

First clone the repository, if you haven't done it already, build all docker
images and boot them up using Docker Compose:

.. code-block:: console

    $ git clone https://github.com/CERNDocumentServer/cds.git
    $ git checkout master
    $ docker-compose build
    $ docker-compose up

Next, create the database, indexes, fixtures and an admin user:

.. code-block:: console

    $ docker-compose run web cds db create
    $ docker-compose run web cds index init
    $ docker-compose run web cds users create cds@cern.ch -a
    $ docker-compose run web cds access allow admin-access -e cds@cern.ch
    $ docker-compose run web cds fixtures cds

Now visit the following URL in your browser:

.. code-block:: console

    https://<docker ip>

You can use the following web interface to inspect Elasticsearch and RabbitMQ:

- Elasticsearch: http://<docker ip>:9200/_plugin/hq/
- RabbitMQ: http://<docker ip>:15672/ (guest/guest)

Also the following ports are exposed on the Docker host:

- ``80``: Nginx
- ``443``: Nginx
- ``5000``: CDS
- ``5432``: PostgreSQL
- ``5672``: RabbitMQ
- ``6379``: Redis
- ``9200``: Elasticsearch
- ``9300``: Elasticsearch
- ``15672``: RabbitMQ management console

**Dependencies**

CDS depends on PostgreSQL, Elasticsearch, Redis and RabbitMQ.
