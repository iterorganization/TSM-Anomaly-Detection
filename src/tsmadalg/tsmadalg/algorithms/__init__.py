"""
Algorithm catalog
=================

Each subfolder of this package is an algorithm package, named in snake_case.
A valid algorithm package must:

- Be a direct subfolder of this directory.
- Contain a ``main.py`` module defining one subclass of
  :class:`tsmadkit.AnomalyDetection`.
- Re-export that class in its ``__init__.py``.

Example structure
-----------------
.. code-block:: text

    algorithms/
        my_algorithm/
            __init__.py     <- from .main import MyAlgorithm
            main.py         <- defines class MyAlgorithm(AnomalyDetection)

Algorithms are imported from their own package, which only imports that
algorithm and its dependencies:

.. code-block:: python

    from tsmadalg.algorithms.my_algorithm import MyAlgorithm

The algorithm packages are discovered by :mod:`tsmadalg.tools.registry`, which
is used by the ``tsmadalg`` CLI.
"""
