.. _documentation-home:

TSM Anomaly Detection Documentation
===================================

This documentation is the user guide for the two Python packages developed in
this repository:

- ``tsmadkit`` is the framework layer. It defines the base class,
  configuration rules, preprocessing helpers, and the standardized
  :class:`tsmadkit.AnomalyResult` output object used by every detector.
- ``tsmadalg`` is the catalog layer. It discovers algorithms packaged under
  ``tsmadalg.algorithms``, tracks their availability in a registry, exposes a
  small CLI, and ships concrete implementations built on top of ``tsmadkit``.

Together, they provide a complete workflow for developing anomaly-detection
algorithms, packaging them consistently, validating their configuration,
running them from Python, and exposing them to downstream systems.

What You Can Find Here
----------------------

Use this documentation as a complete guide to the repository:

- :doc:`getting-started` explains installation, repository layout, and the
  quickest way to instantiate and run an algorithm.
- :doc:`architecture` describes how the two packages fit together, from JSON
  configuration to registry discovery and result serialization.
- :doc:`guides/configuration` documents the JSON configuration schema in detail,
  including the role of every supported key.
- :doc:`guides/reference-state` explains how history and cache management work
  for detectors that compare against historical samples.
- :doc:`guides/create-algorithm` walks through implementing a new detector and
  exposing it to the catalog.
- :doc:`guides/cli` documents the ``tsmadalg`` command-line interface and shows
  how it relates to the Python registry API.
- :doc:`algorithms/index` lists the algorithm pages generated from the
  ``tsmadalg.algorithms`` packages currently present in the source tree.
- :doc:`api/tsmadkit` and :doc:`api/tsmadalg` provide the low-level API
  reference once you already know the overall workflow.

Recommended Reading Order
-------------------------

If you are new to the project, this sequence works well:

1. Read :doc:`getting-started`.
2. Continue with :doc:`architecture`.
3. Read :doc:`guides/configuration` and :doc:`guides/create-algorithm`; check
   :doc:`guides/reference-state` too if your algorithm needs historical
   comparison.
4. Use :doc:`guides/cli` and :doc:`algorithms/index` while developing or
   testing concrete algorithms.
5. Keep :doc:`api/tsmadkit` and :doc:`api/tsmadalg` nearby for exact class and
   function signatures.

Quick Orientation
-----------------

The most important ideas to keep in mind are:

- Every detector is a subclass of :class:`tsmadkit.AnomalyDetection`.
- Every detector is configured from a JSON file that follows the schema
  documented in :doc:`guides/configuration`.
- Configuration signal roles are split between ``signals.targets`` and
  ``signals.context`` and exposed as ``SignalSpec``.
- The caller is responsible for instantiating the class with that JSON file,
  calling ``setup()``, and then calling ``detect()`` (with a ``SignalSet``) or
  ``_tsm_poz_execute()`` (with ``{"time": ..., "values": ...}``).
- Algorithms that need to compare new data against historical samples rather
  than a static trained model can declare a ``reference_state`` in their
  configuration; see :doc:`guides/configuration`.
- ``tsmadalg`` discovers algorithm packages automatically and stores metadata
  such as version, availability status, and import failures in a registry.
- The algorithm catalog pages in :doc:`algorithms/index` are generated from the
  source tree, so they complement the handwritten guides rather than replacing
  them.

.. toctree::
   :hidden:

   Home <self>

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Overview

   getting-started
   architecture

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Guides

   guides/configuration
   guides/reference-state
   guides/create-algorithm
   guides/cli

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Algorithms

   algorithms/index

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: API Reference

   api/tsmadkit
   api/tsmadalg
