Installation
============

Prepare the environment
-----------------------

1. Install ``ffmpeg`` and ensure that ``ffprobe`` is in your PATH:

.. code-block:: console

    $ ffprobe
    ... ffprobe version 3.3.3 ...

2. You will need NodeJS v14. Remember you can use `nvm` to help you manage the NodeJS version.

3. Set up a python virtual environment with python version 3.6. Remember to double check your VIRTUAL_ENV environment variable to ensure later scripts run properly:

.. code-block:: console

    $ echo $VIRTUAL_ENV

If you get an empty output from the previous command, run:

.. code-block:: console

    $ export VIRTUAL_ENV=<path_to_your_env>

4. Activate your virtual environment, create a ``src`` folder, change directories to the ``src`` folder you just created and clone this repo:

.. code-block:: console

    (cds3)$ mkdir src ; cd src
    (cds3)$ git clone https://github.com/CERNDocumentServer/cds-videos.git

5. Run a script to set up some npm configurations and install some packages:

.. code-block:: console

    (cds3)$ ./scripts/setup-npm.sh

6. If you are using linux, downgrade ``setuptools`` and install some important libraries:

.. code-block:: console

    (cds3)$ pip install "setuptools<58.0"
    (cds3)$ sudo apt install libsasl2-dev libldap2-dev libssl-dev curl

7. Install production like setup:

.. code-block:: console

    (cds3)$ pip install -r requirements.pinned.txt
    (cds3)$ pip install -e .

Or just install  latest released versions of all the dependencies:

.. code-block:: console

    (cds3)$ pip install -e .

8. Build the assets:

.. code-block:: console

    (cds3)$ python -O -m compileall .
    (cds3)$ ./scripts/setup-assets.sh

9. Install ``docker`` and ``docker-compose`` - `Docker installation doc <https://docs.docker.com/get-docker/>`

.. code-block:: console

    (cds3)$ sudo apt install docker docker-compose
    (cds3)$ sudo groupadd docker
    (cds3)$ sudo usermod -aG docker $USER
    (cds3)$ newgrp docker

Testing the server locally
--------------------------

1. Create and run your container with the proper configuration:

.. code-block:: console

    (cds3)$ docker-compose up

2. Create database and user:

.. code-block:: console

    (cds3)$ ./scripts/setup-instance.sh

3. (Optional) Fill the database with demo data:

.. code-block:: console

    (cds3)$ cds fixtures records

4. Run example development server:

.. code-block:: console

    (cds3)$ ./script/server

5. Run celery:

.. code-block:: console

    (cds3)$ ./script/celery

Now you can visit https://localhost:5000/ :)

In order to test the video previewer, add the following to your ``/etc/hosts`` file:

    .. code-block:: console

        $ 127.0.0.1  localhost localhost.cern.ch

Now you can visit http://localhost.cern.ch:5000/ :)

Installation errors
-------------------

On MacOS, if you have the error ``pg_config executable not found.``, then you need to install `postgresql` and symlink it:

.. code-block:: console

    $ brew install postgresql@13
    $ export PATH=$PATH:/opt/homebrew/opt/postgresql\@13/bin


On MacOS, if you have the error ``Cairo (pycairo) not found``, then you need to ``python -m pip install pycairo``.


On MacOS, if you have errors with ``cryptography`` and ``openssl``, make sure that you have OpenSSL v1.1:

.. code-block:: console

    $ brew install openssl@1.1
    $ LDFLAGS="-L/opt/homebrew/Cellar/openssl@1.1/1.1.1t/lib" CPPFLAGS="-I/opt/homebrew/Cellar/openssl@1.1/1.1.1t/include" pip install "cryptography==3.3.2"

On MacOS, if you have an error with dynamic linker, check this link:
https://stackoverflow.com/questions/65130080/attributeerror-running-django-site-on-mac-11-0-1

Elasticsearch on ARM-based CPUs
-------------------------------

If you need to run Elasticsearch in ARM-based CPUs, use the `docker/es/Dockerfile.arm64` image instead.