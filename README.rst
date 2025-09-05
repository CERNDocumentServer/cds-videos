..
    Copyright (C) 2013-2024 CERN.
    CDS Videos is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License; see LICENSE file for more details.

==========
CDS Videos
==========

.. image:: https://img.shields.io/github/license/CERNDocumentServer/cds-videos.svg
        :target: ./LICENSE

This is the CDS Videos source code overlay.

Powered by Invenio
===================
CDS Videos is a small layer on top of `Invenio <http://invenio-software.org>`_, a ​free software suite enabling you to run your own ​digital library or document repository on the web.

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
     - `Optional: Upload Additional File <#optional-upload-additional-file>`_
     - `Optional: Update the Access of the Video <#optional-update-the-access-of-the-video>`_
     - `Step 5: Get Video to Check the Flow Status <#step-5-get-video-to-check-the-flow-status>`_
     - `Step 6: Publish Video <#step-6-publish-video>`_
- `Replace the Main Video File through REST API <#replace-the-main-video-file-through-rest-api>`_
     - `General Flow <#general-flow>`_
     - `Alternative: Without Doing the Get Request <#alternative-without-doing-the-get-request>`_


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

To run the tests, follow these steps:

1. **Activate your Python environment:**

2. **Set up the test environment:**

   .. code-block:: bash

      ./scripts/setup-tests

3. **Run the tests:**

   .. code-block:: bash

      ./run-tests.sh


   **Running Specific Tests**
   
   To run a specific test file or function, use the following command:

   .. code-block:: bash

      ./run-tests.sh tests/unit/test_example.py -k "test_specific_function"


Publish Video through REST API
==============================

Generate a Personal Access Token
---------------------------------

- Navigate to the ``CDS Videos`` platform.  
- Click on your user info in the top-right corner.  
- Go to **Applications** and create a new **Personal Access Token**.  
- Copy the token and store it securely.

Using `Bruno`
~~~~~~~~~~~~~

If you'd like to use the pre-configured REST API collection in Bruno, ensure you have the application installed. Follow the steps below to set up and use the collection:

1. **Install Bruno:**  

   Visit the official Bruno `documentation <https://www.usebruno.com/>`_ or repository and install the application.

2. **Import the Collection:**  

   - Download this `Bruno collection <./Bruno%20Collection%20-%20CDS%20Videos%20Publish%20Video.json>`_.
   - Open Bruno and import downloaded collection.
   - Switch to **Developer Mode**.
   - Create an environment for the collection.  
   - Configure the environment by adding a variable named ``baseURL``. Set its value to your API base URL (e.g., ``http://localhost:5000``).

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
     - **Required/Optional**
   * - **category**
     - string
     - body
     - Category of the project.
     - Required
   * - **type**
     - string
     - body
     - Type of the project.
     - Required
   * - **_access**
     - json
     - body
     - Access options for the project.
     - Optional
   * - **contributors**
     - array<object>
     - body
     - List of contributors, including their details.
     - Optional
   * - **description**
     - string
     - body
     - Description of the project.
     - Optional
   * - **title**
     - json
     - body
     - Title of the project.
     - Optional
   * - **keywords**
     - list<json>
     - body
     - Keywords related to the project.
     - Optional


**Body:**

To restrict the project, add ``_access/read``:

.. code-block:: json

   {
      "_access": {
            "update": [
            "admin@test.ch",
            "your-egroup@cern.ch"
         ],
         "read": [
               "your-egroup@cern.ch"
         ]
      },
      "category": "ATLAS",
      "type": "VIDEO",
      "contributors": [
            {
               "name": "Surname, Name",
               "ids": [
                     {
                        "value": "cern id",
                        "source": "cern"
                     }
               ],
               "email": "test@cern.ch",
               "role": "Co-Producer"
            }
         ],
      "title":
         {
         "title":"project title"
         },
      "keywords":[
         {
               "name": "keyword",
               "value": {
                  "name": "keyword"
               }
         },
         {
               "name": "keyword2",
               "value": {
                  "name": "keyword2"
               }
         }
         ],
      "description": "Description"
   }

**Response:**  

Created project JSON. Save ``response.body.project_id`` as ``_project_id`` for later use.


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
     - **Required/Optional**
   * - **_project_id**
     - string
     - body
     - ID of the project.
     - Required
   * - **title**
     - string
     - body
     - Title of the video.
     - Required
   * - **_access**
     - json
     - body
     - Access details for the video.
     - Optional
   * - **vr**
     - boolean
     - body
     - Indicates if the video is 360. 
     - Optional
   * - **contributors**
     - array<object>
     - body
     - List of contributors, including their details.
     - Required
   * - **description**
     - string
     - body
     - Description of the video.
     - Required
   * - **date**
     - string (date)
     - body
     - Date in ``YYYY-MM-DD`` format.
     - Required
   * - **language**
     - string
     - body
     - Language of the video.
     - Required
   * - **featured**
     - boolean
     - body
     - Whether the video is featured. (Available for members of `VIDEOS_EOS_PATH_EGROUPS <./cds/config.py#L1277>`_)
     - Optional
   * - **keywords**
     - list<json>
     - body
     - Keywords related to the video.
     - Optional
   * - **related_links**
     - list<json>
     - body
     - Links related to the video.
     - Optional

**Body:**

To restrict the video, add ``_access/read``. The ``_access/update`` will be the same as the project:

.. code-block:: json

   {
      "_project_id":"{{project_id}}",
      "title":
         {
            "title":"217490_medium"
         },
      "_access": {
         "read": [
               "your-egroup@cern.ch"
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
               "email": "test@cern.ch",
               "role": "Co-Producer"
            }
      ],
      "description": "Description",
      "date": "2024-11-12",
      "keywords":[
         {
            "name": "keyword",
            "value": {
                  "name": "keyword"
            }
         },
         {
            "name": "keyword2",
            "value": {
                  "name": "keyword2"
            }
         }
      ],
      "related_links":[
         {
            "name": "related link",
            "url": "https://relatedlink"
         }
      ],
      "language": "en"
   }

**Response:**  

Created video JSON. Save ``response.body.id`` as ``video_id`` and ``response.body.metadata._buckets.deposit`` as ``bucket_id`` for later use.


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

- To include the file in the body, modify the `pre-request script` in Bruno.

**Response:**  

Uploaded video JSON. Save ``response.body.version_id`` as ``main_file_version_id`` and ``response.body.key`` as ``video_key`` for later use.


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

Created flow JSON. If you want to replace the main video file later, save ``response.body.key`` as ``main_video_key``.


Optional: Upload Additional File
------------------------------------------

**Request:**  

``PUT`` ``{{baseURL}}/api/files/{{bucket_id}}/{{additional_file}}``

**Headers:**  

- ``X-Invenio-File-Tags: context_type=additional_file``

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

- To include the file in the body, modify the `pre-request script` in Bruno.


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
          "your-egroup@cern.ch"
        ],
        "read": [
              "your-egroup@cern.ch"
        ]
     }
    }

**Response:**  

Updated video JSON.


Step 5: Get Video to Check the Flow Status
--------------------------------------------

**Request:**  

``GET`` ``{{baseURL}}/api/deposits/video/{{video_id}}``

**Headers:**  

- ``content-type: application/vnd.project.partial+json``

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

**Response:**  

Updated video JSON with flow status. You can find the flow status in ``response.body.metadata._cds.state``:

.. code-block:: json

    {
      "_cds": {
        "state": {
          "file_transcode": "STARTED",
          "file_video_extract_frames": "SUCCESS",
          "file_video_metadata_extraction": "SUCCESS"
        }
      }
    }


Step 6: Publish Video
----------------------

Before publishing the video, ensure that the workflow is complete.

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


Replace the Main Video File through REST API
============================================

General Flow
------------

1. Get the video (see `Step 5 <#step-5-get-video-to-check-the-flow-status>`_) and find the master file key from the response.

   **Request:**

   ``GET {{baseURL}}/api/deposits/video/{{video_id}}``

   **Headers:**

   - ``content-type: application/vnd.project.partial+json``

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

   **Response:**

   Video JSON. You can find the main file inside ``response.body.metadata._files``.

   .. code-block:: javascript

      let files = data.metadata?._files || [];
      // Find the master file
      let masterFile = files.find(f => f.context_type === "master");
      video_key = masterFile.key;


2. Upload the new video with the same master key and same ``bucket_id`` (see `Step 3 <#step-3-upload-the-video>`_)

   **Upload Request**

   ``PUT {{baseURL}}/api/files/{{bucket_id}}/{{main_video_key}}``

   **Headers:**

   - ``X-Invenio-File-Tags: times_replaced=number_of_times_replaced``

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
      * - **main_video_key**
        - string
        - path
        - Key of the previous main file.
      * - **file**
        - file
        - body
        - The file to be uploaded.

   **Response:**

   Uploaded file JSON. Save version_id and key for later use:

   - ``response.body.version_id`` → ``version_id``  
   - ``response.body.key`` → ``video_key``  



3. Start the flow with your new ``video_key`` and ``version_id`` but keep the same ``bucket_id`` and ``deposit_id`` (see `Step 4 <#step-4-create-a-flow>`_)

   **Request:**

   ``POST /api/flows/``

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


Alternative: Without Doing the Get Request
------------------------------------------

If you want to integrate this process into your workflow **without calling the Get Video request**,  
you must be careful about which **video key** you are using, since it changes during different stages.

**⚠️ Important: Using the Correct Video Key**

The ``video_key`` changes and you must use the correct key depending on when you're performing the replacement:

- **Scenario 1: Replacing after initial file upload (before creating flow)**  

  - Use the ``video_key`` returned from the upload file request response.

- **Scenario 2: Replacing after creating the flow (before publishing)**  

  - Use the ``key`` value from the Create Flow response.

      This is required because the backend **renames the uploaded file** to distinguish it from automatically generated subformat files.

- **Scenario 3: Replacing after publishing the video**

  - First make an edit request to modify the published video.  

  - ``POST {{baseURL}}/api/deposits/video/{{deposit_id}}/actions/edit``  

  - Find the master file key from the response:

       .. code-block:: javascript

          let files = data.metadata?._files || [];
          // Find the master file
          let masterFile = files.find(f => f.context_type === "master");
          video_key = masterFile.key;

  - Use this ``video_key`` for the replacement request.  


Do **not** use the original video file name (``video_name``) for replacement requests,  
as this will not work due to the backend file renaming process.

After finding the correct key, you can upload your new file (see `Step 3 <#step-3-upload-the-video>`_).

Then, start the flow again using the new main video file, along with the updated ``version_id`` and ``video_key``.  
You can follow the same structure outlined in `Step 4 <#step-4-create-a-flow>`_.
