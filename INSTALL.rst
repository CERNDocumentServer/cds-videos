==============================
CDS installation
==============================

You should follow the way it's done for the Invenio Demosite with two added
details.

CDS has a bower-base.json file hence, they must be downloaded and collected as
well.

.. code-block:: console

    $ inveniomanage -i bower-base.json > bower.json
    $ bower install
    $ inveniomanage collect
