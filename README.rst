========================
HERE QGIS Python Library
========================


.. image:: https://img.shields.io/badge/License-MIT%20license-blue.svg
    :target: LICENSE



**HERE QGIS Python Library** consists of 2 main components
    + **HERE QGIS Plugin**: integrating seamlessly HERE Mapmaking and services into QGIS.
    + Shared Python modules: interfacing HERE Mapmaking and services.
**HERE QGIS Plugin** empowers GIS, Mapmaking, data teams and enthusiasts to analyze, edit, and publish HERE maps and data directly in QGIS - securely and efficiently.


**Contributing**: `CONTRIBUTING.rst <CONTRIBUTING.rst>`_

**License**: MIT license, Copyright (c) 2026 HERE Europe B.V.

Key Features
--------

The HERE QGIS Plugin is a modular, Python-based integration that connects QGIS with HERE MapMaking and platform services. It enables users to seamlessly visualize, explore, analyze, and edit geospatial data directly within QGIS, bridging HERE's proprietary ecosystem with a widely used open-source GIS environment.

+ Deep Integration with HERE Platform
    + Direct access to HERE MapMaking projects, datasets (e.g., IML/VML), and APIs such as raster tiles, geocoding, and routing for enriched geospatial workflows.

+ Data Visualization and Exploration
    + Load, browse, and visualize multiple map layers with styling options, enabling interactive exploration and analysis of spatial data.

+ Map Editing and Analysis
    + Supports editing and validation of map data, including comparing datasets, identifying inconsistencies, and analyzing data quality across the production pipeline.

+ Flexible Data Handling
    + Efficient loading and processing of geospatial data (e.g., flattening nested GeoJSON structures), making complex datasets easier to work with in QGIS.

+ User-Friendly and Extensible Architecture
    + Designed as a modular framework that allows both non-technical users and advanced GIS/Python developers to experiment, prototype, and extend functionality with additional services.

+ Workflow Acceleration & Experimentation
    + Acts as a "playground" to quickly implement ideas and build reusable GIS tools, accelerating innovation and enabling rapid prototyping of geospatial use cases.

+ Cross-platform and portability
    + QGIS 3.x and QGIS 4 (Qt5 & Qt6)
    + Windows, macOS, Linux
    + One-click dependency installation

Installation
------------

Download and install QGIS
--------------------

+ Supported QGIS version: **QGIS 3.34 and higher**.
+ Download the official QGIS Long Term Release (LTR): `QGIS Download Page <https://qgis.org/en/site/forusers/download.html>`_

Download and install QGIS on MacOS (recommended via pixi)
----------------------------

On macOS, the official QGIS build may include outdated dependencies.
For a more modern and isolated environment, we recommend installing QGIS via **pixi**.

Install pixi via command line

.. code-block:: bash

   curl -fsSL https://pixi.sh/install.sh | sh

Install and run QGIS with pixi

.. code-block:: bash

   # initialize a pixi environment
   pixi init qgis-env
   cd qgis-env

   # install qgis and required dependencies
   pixi add qgis libgdal-arrow-parquet duckdb

   # start QGIS
   pixi run qgis

For subsequent QGIS runs, use:

.. code-block:: bash

   cd qgis-env
   pixi run qgis


Credits
-------

`AUTHORS.rst <AUTHORS.rst>`_
