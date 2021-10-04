Installation
============

Step-by-step
------------

Install `ffmpeg` and ensure that `ffprobe` is in your PATH:

.. code-block:: console

    $ ffprobe
    ... ffprobe version 3.3.3 ...

Prepare the environment. You will need NodeJS v8:

.. code-block:: console

    $ ./scripts/setup-npm.sh
    $ mkvirtualenv cds3
    (cds3)$ cdvirtualenv ; mkdir src ; cd src
    (cds3)$ git clone https://github.com/CERNDocumentServer/cds-videos.git

.. note::

    Before starting the installation you can verify you have installed all the
    system requirements using the `Invenio scripts <https://github.com/inveniosoftware/invenio/tree/master/scripts>`_


Install production like setup

.. code-block:: console

    $ workon cds3
    (cds3)$ cd cds
    (cds3)$ pip install -r requirements.pinned.txt
    (cds3)$ pip install -e .

Or to install the latest released versions of all the dependencies

.. code-block:: console

    $ workon cds3
    (cds3)$ cd cds
    (cds3)$ pip install -e .

Build the assets

.. code-block:: console

    (cds3)$ python -O -m compileall .
    (cds3)$ ./scripts/setup-assets.sh

Make sure that ``elasticsearch`` server is running:

.. code-block:: console

    $ elasticsearch
    ... version[2.0.0] ...

Create database & user

.. code-block:: console

    (cds3)$ ./scripts/setup-instance.sh

Fill the database with demo data

.. code-block:: console

    (cds3)$ cds fixtures records

Run example development server:

.. code-block:: console

    (cds3)$ ./script/server

Run celery:

.. code-block:: console

    (cds3)$ ./script/celery

If you are running MacOS Big Sur and you have an error with dynamic linker, check this link:
https://stackoverflow.com/questions/65130080/attributeerror-running-django-site-on-mac-11-0-1

Now you can visit http://localhost:5000/ :)

In order to test the video previewer:

    Add the following to your /etc/hosts file:

    .. code-block:: console

        $ 127.0.0.1  localhost.cern.ch

Now you can visit http://localhost.cern.ch:5000/ :)