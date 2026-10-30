.. _getting-started-guide:

Getting Started
===============

This page is the fastest way to understand what to install, what each package
does, and how a normal anomaly-detection workflow looks in practice.

Two Packages, One Workflow
--------------------------

This repository contains two related Python packages:

- ``tsmadkit``: the framework package. It defines the base class, shared
  configuration handling, model-loading helpers, preprocessing utilities, and
  the :class:`tsmadkit.AnomalyResult` output format.
- ``tsmadalg``: the catalog package. It depends on ``tsmadkit`` and provides
  algorithm discovery, a registry, a CLI, templates for new algorithms, and the
  concrete implementations shipped in this repository.

In day-to-day use, the usual pattern is:

1. Install ``tsmadkit`` and ``tsmadalg``.
2. Choose or implement an algorithm class.
3. Prepare a JSON configuration file.
4. Instantiate the class with that configuration file.
5. Call ``setup()``.
6. Call ``detect()`` on input data.

Repository Layout
-----------------

At a high level, the repository is organized as follows:

.. treeview::
  - :dir:`folder` anomaly_detection_algorithms

    - :dir:`folder` docs        ``(Sphinx documentation)``
    - :dir:`folder` examples    ``(Example algorithms and notebooks)``
    - :dir:`folder` src

      - :dir:`folder` tsmadkit  ``(Core framework package)``
      - :dir:`folder` tsmadalg  ``(Algorithm catalog package)``

    - :dir:`folder` tests       ``(Unit and integration tests)``


The package-specific README files are still useful for quick summaries, but the
goal of this Sphinx documentation is to describe the whole system in one place.

Installation
------------

For local development, install both packages in editable mode. Install
``tsmadkit`` first because ``tsmadalg`` imports it.

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate
   pip install -e src/tsmadkit
   pip install -e src/tsmadalg

Optional extras are available:

.. code-block:: bash

   pip install -e src/tsmadkit[ml]
   pip install -e src/tsmadkit[analysis]
   pip install -e src/tsmadkit[dev]
   pip install -e src/tsmadalg[tools]
   pip install -e src/tsmadalg[dev]

Use the ``ml`` extra when algorithms rely on machine-learning dependencies that
are not part of the minimal installation, and the ``analysis`` extra for
:meth:`tsmadkit.AnomalyResult.to_dataframe`. Use the ``tsmadalg[tools]`` extra
to use the ``tsmadalg`` CLI (it depends on ``rich``). Use the ``dev`` extras
when running the test suite or working on the packages themselves.

Your First Runtime Flow
-----------------------

The simplest way to run a packaged algorithm is to import its class from its
package in ``tsmadalg.algorithms``, instantiate it with a configuration file,
and call ``detect()`` on a :class:`SignalSet`.

.. code-block:: python

   from tsmadalg.algorithms.mag_power_supply import MAGPowerSupply
   from tsmadkit.signals import SignalSet

   detector = MAGPowerSupply("path/to/config.json")
   detector.setup()

   data_dict = {
       "time": [0.0, 0.1, 0.2],
       "values": {
           "sensor_0": [1.2, 1.3, 1.1],
           "sensor_1": [4.0, 3.9, 4.1],
       },
   }

   signals = SignalSet(data_dict, detector.signal_spec)
   result = detector.detect(signals)

``detect()`` always returns a structured :class:`AnomalyResult`.
The TSM POZ application (C++) instead calls ``_tsm_poz_execute()``, which
takes the raw ``data_dict`` directly and returns a plain, serializable tuple;
see :doc:`architecture` for that path.

Understanding the Result Object
-------------------------------

:class:`tsmadkit.AnomalyResult` always contains ``is_anomaly``, plus optional
``label``, ``scores``, ``sources``, and ``message`` fields. See
:doc:`guides/create-algorithm` for guidance on populating them, and
:meth:`tsmadkit.AnomalyResult.to_dataframe` for collecting many results into a
table.

Configuration Comes First
--------------------------

Every detector is created from a JSON configuration file, validated against a
schema before the instance becomes usable. A minimal configuration only needs
``name`` and ``signals``:

.. code-block:: json

   {
       "name": "my-detector",
       "signals": {
           "targets": ["sensor_0", "sensor_1"]
       },
       "parameters": {
           "threshold": 0.5
       }
   }

Each ``parameters`` entry becomes an attribute on the detector instance (e.g.
``self.threshold`` above). See :doc:`guides/configuration` for the complete
schema and :doc:`architecture` for how configuration becomes runtime state.

Detectors That Compare Against History
----------------------------------------

Some detectors compare the current input against historical samples instead
of (or in addition to) a static trained model: declare a ``reference_state``
in the configuration and implement ``transform()``. See
:doc:`guides/configuration` and :doc:`guides/create-algorithm` for the
details.

Using the Catalog
-----------------

The ``tsmadalg`` CLI is useful throughout the algorithm lifecycle:

- ``tsmadalg list`` shows all discovered algorithm packages and their status.
- ``tsmadalg create`` generates a new algorithm skeleton.
- ``tsmadalg run`` runs a registered algorithm on an input payload from the
  command line, without writing any Python.

See :doc:`guides/cli` for the full CLI reference and :doc:`algorithms/index`
for the currently packaged algorithms.

Next Steps
----------

The best follow-up pages are:

- :doc:`architecture` for the complete package relationship and runtime flow.
- :doc:`guides/configuration` for the JSON configuration schema and runtime
  behavior.
- :doc:`guides/create-algorithm` for implementing a new detector.
- :doc:`algorithms/index` for the currently packaged algorithms.
