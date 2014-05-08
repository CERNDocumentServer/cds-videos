===========
CDS overlay
===========

This is CDS demo site source code overlay.

Installation
============

Here, we are assuming that you've already installed invenio 2.0 and will only
focus on installing the CDS overlay.

.. code-block:: console

   (invenio)$ pip install -e .
   (invenio)$ inveniomanage demosite create --packages=cds_demosite.base
   (invenio)$ inveniomanage demosite populate --packages=cds_demosite.base
