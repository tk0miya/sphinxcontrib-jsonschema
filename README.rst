sphinxcontrib-jsonschema
========================

`sphinxcontrib-jsonschema` is Sphinx extension to define data structure using `JSON Schema`_

.. _JSON Schema: http://json-schema.org/

Usage
-----

Include this extension in conf.py::

    extensions = ['sphinxcontrib.jsonschema']

Write ``jsonschema`` directive into reST file where you want to import schema::

    .. jsonschema:: path/to/your.json
