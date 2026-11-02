.. _cli-guide:

``tsmadalg`` Command-Line Interface
===================================

The ``tsmadalg`` package exposes a small CLI for working with the algorithm
catalog. It is mainly a development and inspection tool: it helps you discover
what the registry can see and scaffold new algorithm packages from the expected
layout.

Overview
--------

The top-level command is:

.. code-block:: bash

   tsmadalg --help

The currently defined subcommands are:

- ``tsmadalg list``
- ``tsmadalg create``
- ``tsmadalg run``

``tsmadalg list``
-----------------

Use this command to inspect the algorithm registry:

.. code-block:: bash

   tsmadalg list

It prints a table with:

- algorithm name
- version declared by the class ``__version__``
- availability status
- module/class (when available) or the import error message

This command is especially useful after adding a new algorithm package because it
shows not only successful discoveries but also failures caused by missing
dependencies or import-time exceptions.

The command is backed by :func:`tsmadalg.tools.registry.list_algorithms`, so the
CLI view and the Python API view use the same registry data.

``tsmadalg create``
-------------------

Use this command to generate a new algorithm skeleton:

.. code-block:: bash

   tsmadalg create my_detector

By default, the template:

- creates a new package under ``tsmadalg/algorithms`` (or under
  ``--output-dir`` if provided)
- generates ``main.py`` with a class inheriting from ``AnomalyDetection``
  (``my_detector`` -> ``MyDetector``)
- generates ``example_config.json``
- creates an ``__init__.py`` re-exporting the class
- inserts a placeholder for ``__version__``

Useful options:

.. code-block:: bash

   tsmadalg create my_detector \
       --version 1.0.0 \
       --signals SIGNAL_1 SIGNAL_2 \
       --context-signals CTX_1 \
       --model-source scikit-learn \
       --model-path model.joblib

Supported options are:

- ``--version``: set the initial class version string
- ``--signals``/``--target-signals``: pre-populate target signal names in
  ``example_config.json``
- ``--context-signals``: pre-populate context signal names
- ``--parameters``: initial ``parameters`` object, as a JSON string
- ``--model-source``/``--model-path``: pre-populate the ``model`` section
- ``--anomaly-classes``: pre-populate ``anomaly_classes``
- ``--artifacts``: pre-populate ``artifacts``
- ``--output-dir``: directory where the algorithm folder is created
- ``--overwrite``: replace files if the target directory already exists

The CLI delegates to
:func:`tsmadalg.tools.templates.templates.generate_algorithm_template`. That
function is also available from Python if you prefer to automate template
generation programmatically.

``tsmadalg run``
----------------

The CLI defines a ``run`` subcommand:

.. code-block:: bash

   tsmadalg run my_algorithm --config path/to/config.json --input path/to/data.json

It:

1. resolves the algorithm class through the registry
2. instantiates it from ``--config`` and calls ``setup()``
3. loads and validates the input payload from ``--input`` (the ``time``/``values``
   format described in :doc:`/guides/configuration`)
4. calls ``detect()`` on the resulting :class:`tsmadkit.signals.SignalSet`
5. writes the resulting :class:`tsmadkit.AnomalyResult` to JSON (``--output``,
   defaulting to ``<algo_name>_result.json``)

This is a convenient way to smoke-test an algorithm end to end without writing
any Python.

Relationship to the Registry API
--------------------------------

The CLI is a thin layer on top of the Python APIs in
:mod:`tsmadalg.tools.registry`:

- ``tsmadalg list`` corresponds to
  :func:`tsmadalg.tools.registry.list_algorithms`
- the ``run`` implementation starts by calling
  :func:`tsmadalg.tools.registry.get_algorithm_class`

That means you can move easily between the shell and Python. For example:

.. code-block:: python

   from tsmadalg.tools.registry import get_algorithm_class, list_algorithms

   print(list_algorithms())
   Detector = get_algorithm_class("mag_power_supply")

Recommended Workflow
--------------------

During development, the CLI is most useful in this sequence:

1. Run ``tsmadalg create`` to generate the skeleton.
2. Implement the detector in ``main.py`` and update ``example_config.json``.
3. Run ``tsmadalg list`` to confirm that discovery succeeds and to inspect the
   reported version, imports, and status.

If you want the implementation details behind that workflow, see
:doc:`/guides/create-algorithm`. For the generated algorithm pages, see
:doc:`/algorithms/index`.
