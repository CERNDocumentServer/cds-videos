===
CDS
===

This is the CERN Document Server source code overlay.

Powered by Invenio
===================
CDS is a small layer on top of `Invenio <http://invenio-software.org>`_, a ​free software suite enabling you to run your own ​digital library or document repository on the web.

Table of Contents
=================

- `Prerequisites <#prerequisites>`_
- `Update Dependencies <#update-dependencies>`_
- `Installation and Setup <#installation-and-setup>`_
     - `1. Clone the Repository <#1-clone-the-repository>`_
     - `2. Start Docker <#2-start-docker>`_
     - `3. Run Setup Scripts <#3-run-setup-scripts>`_
     - `4. Local Development <#4-local-development>`_
- `Testing <#testing>`_
- `Publish Video through REST API <#publish-video-through-rest-api>`_
     - `Generate a Personal Access Token <#generate-a-personal-access-token>`_
     - `Step 1: Create a Project <#step-1-create-a-project>`_
     - `Step 2: Create a Video <#step-2-create-a-video>`_
     - `Step 3: Upload the Video <#step-3-upload-the-video>`_
     - `Step 4: Create a Flow <#step-4-create-a-flow>`_
     - `Step 5: (Optional) Upload Additional File <#step-5-optional-upload-additional-file>`_
     - `Step 6: Publish Video <#step-6-publish-video>`_
     - `Optional: Update the Access of the Video <#optional-update-the-access-of-the-video>`_
     - `Optional: Get Project Status <#optional-get-project-status>`_
- `License <#license>`_


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


Publish Video through REST API
==============================

Generate a Personal Access Token
---------------------------------

   - Navigate to the ``CDS Videos`` platform.  
   - Click your user info in the top-right corner.  
   - Go to **Applications** and create a new **Personal Access Token**.  
   - Copy the token and store it securely.

Using `Bruno`
~~~~~~~~~~~~~

If you'd like to use the pre-configured REST API collection in Bruno, ensure you have the application installed. Follow the steps below to set up and use the collection:

1. **Install Bruno:**  

   Visit the official Bruno `Bruno collection <./Bruno Collection - CDS Videos Publish Video.json>`_ or repository and install the application.

2. **Create an Environment for the Collection:**  

   - Open Bruno and import this [collection](https://link).
   - Create an environment for the collection.  
   - Configure the environment by adding a variable named ``baseURl``. Set its value to your API base URL (e.g., ``http://localhost:5000``).

3. **Configure Authentication in Bruno:**  

   - In Bruno, open the **Collection Settings**.  
   - Go to **Auth** and set the **Bearer Token** to your Personal Access Token.  


Step 1: Create a Project
------------------------

**Request:**  

``POST`` ``{{baseURL}}/api/deposits/project/``

**Headers:**  

- ``content-type: application/vnd.project.partial+json``
  
**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **$schema**
     - string
     - body
     - Schema URL for the project creation.
   * - **category**
     - string
     - body
     - Category of the project.
   * - **type**
     - string
     - body
     - Type of the project.
   * - **_access**
     - json
     - body
     - Access options for the video.

**Body:**

To restrict the project, add ``_access/read``:

.. code-block:: json

    {
        "$schema": "https://localhost:5000/schemas/deposits/records/videos/project/project-v1.0.0.json",
        "_access": {
            "update": [
              "admin@test.ch",
              "atlas-outreach-cds-video@cern.ch"
            ],
            "read": [ 
                "atlas-readaccess-active-members@cern.ch"
            ]
        },
        "category": "ATLAS",
        "type": "VIDEO"
    }

**Response:**  

Created project JSON.


Step 2: Create a Video
----------------------

**Request:**  

``POST`` ``{{baseURL}}/api/deposits/video/``

**Headers:**  

- ``content-type: application/vnd.video.partial+json``
  
**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **$schema**
     - string
     - body
     - Schema URL for video creation.
   * - **_project_id**
     - string
     - body
     - ID of the project.
   * - **title**
     - string
     - body
     - Title of the video.
   * - **_access**
     - json, optional
     - body
     - Access details for the project.
   * - **vr**
     - boolean
     - body
     - 
   * - **contributors**
     - array<object>
     - body
     - List of contributors, including their details.
   * - **description**
     - string
     - body
     - Description of the video.
   * - **date**
     - string (date)
     - body
     - Date in ``YYYY-MM-DD`` format.
   * - **language**
     - string
     - body
     - Language of the video.
   * - **featured**
     - boolean
     - body
     - Whether the video is featured.

**Body:**

To restrict the video, add ``_access/read``. The `_access/update` will be the same as the project:

.. code-block:: json

    {
      "$schema":"https://localhost:5000/schemas/deposits/records/videos/video/video-v1.0.0.json",
     "_project_id":"{{project_id}}",
      "title": {
        "title":"217490_medium"
      },
      "_access": {
          "read": [
                "atlas-readaccess-active-members@cern.ch"
            ]
      },
      "vr": false,
      "featured": false,
      "language": "en",
      "contributors": [
          {
              "name": "Surname, Name",
              "ids": [
                  {
                      "value": "cern id",
                      "source": "cern"
                  }
              ],
              "email": "email@cern.ch",
              "role": "Co-Producer"
          }
      ],
      "description": "Description",
      "date": "2024-11-12"
    }

**Response:**  

Created video JSON.


Step 3: Upload the Video
------------------------

**Request:**  

``PUT`` ``{{baseURL}}/api/files/{{bucket_id}}/{{video_name}}``

**Headers:**  

- ``content-type: video/mp4``
- ``Accept: application/json, text/plain, */*``
- ``Accept-Encoding: gzip, deflate, br, zstd``

**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **bucket_id**
     - string
     - path
     - Bucket ID.
   * - **video_name**
     - string
     - path
     - Name of the video file.
   * - **file**
     - object
     - body
     - Video file.


**Response:**  

Uploaded video JSON.


Step 4: Create a Flow
----------------------

**Request:**  

``POST`` ``/api/flows/``

**Headers:**  

- ``content-type: application/vnd.project.partial+json``
  
**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **version_id**
     - string
     - body
     - Version ID from the uploaded video response.
   * - **key**
     - string
     - body
     - Video key from the uploaded video response.
   * - **bucket_id**
     - string
     - body
     - Bucket ID from the Create Video response.
   * - **deposit_id**
     - string
     - body
     - Deposit ID from the Create Video response.

**Body:**

.. code-block:: json

    {
      "version_id": "{{main_file_version_id}}",
      "key": "{{video_key}}",
      "bucket_id": "{{bucket_id}}",
      "deposit_id": "{{video_id}}"
    }

**Response:**  

Created flow JSON.


Step 5: (Optional) Upload Additional File
------------------------------------------

**Request:**  

``PUT`` ``{{baseURL}}/api/files/{{bucket_id}}/{{additional_file}}``

**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **bucket_id**
     - string
     - path
     - ID of the bucket to upload the file.
   * - **file_name**
     - string
     - path
     - Name of the file.
   * - **file**
     - file
     - body
     - The file to be uploaded.

**Response:**  

Uploaded additional file JSON.

Step 6: Publish Video
----------------------

**Request:**  

``POST`` ``{{baseURL}}/api/deposits/video/{{video_id}}/actions/publish``

**Headers:**  

- ``content-type: application/json``

**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **video_id**
     - string
     - path
     - ID of the video  to publish.


**Response:**  

Published video deposit JSON.

Optional: Update the Access of the Video
----------------------------------------

**Request:**  

``PUT`` ``{{baseURL}}/api/deposits/video/{{video_id}}``

**Headers:**  

- ``content-type: application/vnd.video.partial+json``

**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **video_id**
     - string
     - path
     - ID of the video.

**Body:**  

To restrict the video, add ``_access/read``. If you want to change the access/update permissions, replace the email addresses in the ``update`` field accordingly.

.. code-block:: json

    {
     "_access": {
        "update": [
          "admin@test.ch",
          "atlas-outreach-cds-video@cern.ch"
        ],
        "read": [
              "atlas-readaccess-active-members@cern.ch"
        ]
     }
    }

**Response:**  

Updated video JSON.


Optional: Get Project Status
---------------------------

**Request:**  

``GET`` ``{{baseURL}}/api/deposits/project/{{project_id}}``

**Headers:**  

- ``content-type: application/vnd.project.partial+json``

**Parameters:**

.. list-table:: 
   :header-rows: 1

   * - **Name**
     - **Type**
     - **Location**
     - **Description**
   * - **project_id**
     - string
     - path
     - ID of the project.

**Response:**  

Updated project JSON with flow status as ``state``:

.. code-block:: json

    {
      "id": "b320568fc1264dda90a8f459be42892e",
      "_cds": {
        "state": {
          "file_transcode": "STARTED",
          "file_video_extract_frames": "SUCCESS",
          "file_video_metadata_extraction": "SUCCESS"
        }
      }
    }


License
=======

Copyright (C) 2013-2024 CERN.

CDS is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

CDS is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with CDS; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

In applying this licence, CERN does not waive the privileges and immunities granted to it by virtue of its status as an Intergovernmental Organization or submit itself to any jurisdiction.

