.. _algorithm-catalog:

Algorithm Catalog
=================

This section contains the per-algorithm pages generated automatically from the
packages found in ``src/tsmadalg/tsmadalg/algorithms``.

What These Pages Contain
------------------------

For each algorithm package, the documentation generator includes:

- the algorithm package README when present
- the package ``example_config.json`` when present
- autodoc output for the implementation module in ``main.py``

These generated pages are useful when you want package-specific information such
as the example configuration or the implementation docstrings of a concrete
algorithm.

How to Interpret the Catalog
----------------------------

Keep the following distinctions in mind:

- The generated pages are based on the source tree, so they document algorithm
  packages that exist in the repository.
- The runtime registry described in :doc:`../architecture` tracks whether those
  packages are actually importable in the current Python environment.
- ``tsmadalg list`` is therefore the authoritative runtime view when you want to
  know whether an algorithm is available or which dependency failed to import.

If you are looking for the general detector contract rather than one specific
implementation, start with :doc:`../guides/create-algorithm` and
:doc:`../guides/configuration`.

Available Algorithms
--------------------

.. toctree::
   :maxdepth: 1
   :glob:

   generated/*

.. note::

   Each page is generated automatically during the Sphinx build from the
   corresponding package under ``tsmadalg.algorithms``.
