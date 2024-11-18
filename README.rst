===
CDS
===

This is the CERN Document Server source code overlay.

Powered by Invenio
===================
CDS is a small layer on top of `Invenio <http://invenio-software.org>`_, a ​free software suite enabling you to run your own ​digital library or document repository on the web.

Prerequisites
=============

Ensure that the following dependencies are installed with the specified versions:

1. **Python 3.9**

2. **Node.js v18**

3. **FFmpeg v5.0**

4. **Docker v2 or later:**
   If Docker is not already installed, download and install Docker Desktop from the `official Docker website <https://www.docker.com/products/docker-desktop/>`_.

Update dependencies
======================

To update Python dependencies you need to run `npm install` in the target deployment environment:

.. code-block:: shell

    $ docker run -it --platform="linux/amd64" --rm -v $(pwd):/app -w /app \
        registry.cern.ch/inveniosoftware/almalinux:1 \
        sh -c "dnf install -y openldap-devel && pip install -e . && pip freeze > requirements.new.txt"

Installation and Setup
======================

1. Clone the Repository
-----------------------

Begin by cloning this repository and navigating to the project directory:

.. code-block:: bash

   git clone https://github.com/CERNDocumentServer/cds-videos.git
   cd cds-videos

2. Start Docker
-----------------------

Use Docker Compose to start the required containers in detached mode:

.. code-block:: bash

   docker compose up -d

3. Run Setup Scripts
-----------------------

The ``scripts`` folder contains the necessary setup scripts to initialize and configure your instance.

**1. Bootstrap Script**
   Initialize the environment by running the bootstrap script:

   .. code-block:: bash

      ./scripts/bootstrap

   **Troubleshooting**:

      These are the macOS solutions using ``brew`` for installation.

      If you encounter the error ``pg_config executable not found``, you may need to install PostgreSQL and update the PATH:

      .. code-block:: bash

         brew install postgresql@14
         export PATH=$PATH:/opt/homebrew/opt/postgresql@14/bin

      For errors related to missing ``cmake`` and ``ninja`` tools ``ERROR: Command errored out with exit status 1 ... "cmake>=3.14" "ninja>=1.5"``:

      Install ``cmake`` and ``ninja`` with the following command:

      .. code-block:: bash

         brew install cmake ninja

      If you encounter errors with ``cryptography`` and ``OpenSSL``, ensure that OpenSSL version 3 is installed:

      .. code-block:: bash

         brew install openssl@3

**2. Setup Script**
   Run the setup script to finalize the installation and configuration:

   .. code-block:: bash

      ./scripts/setup

   **Troubleshooting**:
   If you encounter the error ``connection to server at "localhost", port 5432 failed: FATAL: role ".." does not exist``, it may indicate an issue with the database role or a port conflict. To diagnose:

      1. First, connect to the Docker database container and verify that the expected role exists and the database is working correctly.

         .. code-block:: bash

            docker exec -it <db_container_name> psql -U <username> -d <database>

      2. If the role is present and the database is functional, check for port conflicts on port 5432:

         .. code-block:: bash

            lsof -i :5432

        Terminate any conflicting process if found, and restart Docker.


4. Local Development
-----------------------

To facilitate local development, open multiple terminal sessions and run the following commands separately:

- **Start Web Server**
  This command launches the web server:

  .. code-block:: bash

     ./scripts/server

- **Start Celery Workers**
  Celery workers are required for background task processing:

  .. code-block:: bash

     ./scripts/celery

- **Watch Frontend Code**
  This command watches frontend code for changes and rebuilds assets as needed:

  .. code-block:: bash

     ./scripts/assets-watch


Testing
=======
Running the tests are as simple as: ::

    python setup.py test

or (to also show test coverage) ::

    source run-tests.sh

License
=======

Copyright (C) 2013-2024 CERN.

CDS is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

CDS is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with CDS; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

In applying this licence, CERN does not waive the privileges and immunities granted to it by virtue of its status as an Intergovernmental Organization or submit itself to any jurisdiction.

