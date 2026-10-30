.. _create-algorithm-guide:

Create a New Algorithm
======================

This guide explains the complete contract for implementing a new detector and
making it discoverable through ``tsmadalg``.

The short version is:

1. Create a new package under ``tsmadalg/algorithms``.
2. Add a valid ``example_config.json`` file.
3. Implement the detector class in ``main.py``.
4. Call ``tsmadalg list`` or use the registry API to verify discovery.

Every detector is a subclass of :class:`tsmadkit.AnomalyDetection`. Detectors
that only look at the current input just implement ``detect()``. Detectors
that also compare the current input against historical samples declare a
``reference_state`` in their configuration and implement ``transform()`` too;
see :doc:`/guides/reference-state` for how that mechanism works and
:ref:`reference-state-example` below for the implementation pattern.

Required Package Layout
-----------------------

Each algorithm must live in its own subpackage under
``src/tsmadalg/tsmadalg/algorithms``:

.. treeview::
  - :dir:`folder` tsmadalg

    - :dir:`folder` algorithms

      - :dir:`folder` my_algorithm

        - :dir:`file` __init__.py
        - :dir:`file` main.py
        - :dir:`file` example_config.json


These files are not optional:

- ``main.py`` must define exactly one subclass of ``AnomalyDetection``.
- ``__init__.py`` marks the folder as a Python package and re-exports the
  algorithm class (e.g. ``from .main import MyAlgorithm``).
- ``example_config.json`` shows what a real configuration looks like for this
  algorithm (expected parameters, signals, model) and is used by the generated
  algorithm documentation page.

The directory name becomes the registry key used by
:func:`tsmadalg.tools.registry.get_algorithm_class` and by the ``tsmadalg list``
output, so choose it following the :ref:`naming-convention`. It is also the
algorithm's import path:

.. code-block:: python

   from tsmadalg.algorithms.my_algorithm import MyAlgorithm

This only imports ``my_algorithm`` and its dependencies, not the other
algorithms.

.. _naming-convention:

Naming Convention
-----------------

An algorithm is named after the ITER system it monitors, followed by either a
subsystem of that system or a phenomenon it detects, in snake_case:

.. code-block:: text

   <system>_<subsystem or phenomenon>[_<qualifier>]

- ``system`` is the short code of the system where the anomaly shows up (e.g.
  ``ech``, ``mag``, ``vv``). Systems that only provide context signals are not
  part of the name.
- The subsystem (e.g. ``ech_collector``, ``mag_power_supply``) or the
  phenomenon (e.g. ``mag_quench``, ``vv_stray``) is spelled out, unless its
  abbreviation is universal.
- The optional ``qualifier`` is only added to tell apart two algorithms that
  would otherwise share a name. Prefer the monitored quantity or the source
  (e.g. ``ech_collector_thermal``, ``vv_stray_ech``), and use the detection
  method only as a last resort.

The execution mode (intershot or synchronized), the detection method, and the
properties declared in the configuration (anomaly classes, model) are not part
of the name, so it stays stable across versions.

The class name is the package name in PascalCase, with the system code in
capitals: ``ech_collector`` defines ``ECHCollector``.

Minimal Single-Input Example
----------------------------

The following example shows a small threshold detector, defined in
``threshold_detector/main.py``: each target signal has its own threshold, and
any signal whose maximum value exceeds it is reported as anomalous.

.. code-block:: python

   import numpy as np

   from tsmadkit import AnomalyDetection, AnomalyResult
   from tsmadkit.signals import SignalSet


   class ThresholdDetector(AnomalyDetection):
       __version__ = "0.1.0"

       def detect(self, signals: SignalSet) -> AnomalyResult:
           thresholds = np.asarray(self.thresholds)
           max_values = np.max(signals.target_values, axis=1)
           exceeded = max_values > thresholds

           return AnomalyResult(
               is_anomaly=bool(exceeded.any()),
               scores={"max_value": float(max_values.max())},
               sources=list(signals.target_names[exceeded]) or None,
           )

Important details in that example:

- The class inherits from :class:`tsmadkit.AnomalyDetection`.
- ``__version__`` is required. It is reported in the registry, in ``tsmadalg list``
  and with every result, and changing it invalidates the reference state cache.
- Dependencies such as ``numpy`` are imported normally at module level.
- ``self.thresholds`` comes straight from the JSON ``parameters`` object, one
  entry per target signal.
- ``detect()`` returns :class:`tsmadkit.AnomalyResult`, not a raw dictionary.

Matching Configuration
----------------------

The example above needs a configuration file whose ``parameters`` entry
defines one threshold per target signal:

.. code-block:: json

   {
       "name": "threshold-detector",
       "signals": {
           "targets": ["sensor_0", "sensor_1"]
       },
       "parameters": {
           "thresholds": [1.0, 2.0]
       }
   }

See :doc:`/guides/configuration` for the full schema and runtime behavior of
each key.

The Implementation Contract
---------------------------

Every algorithm should follow the same mental model.

Constructor
~~~~~~~~~~~

The constructor is inherited from the base class. You do not override it. It
loads and validates the configuration, and stores the attributes described in
:doc:`/guides/configuration`.

``setup()``
~~~~~~~~~~~

Call ``setup()`` once after construction and before inference. Its default
behavior (built-in model loading, reference-state preparation) is described in
:doc:`/architecture`. Override it only when your model needs a custom loading
procedure (``model.source: "custom"``) or you need extra one-time
preprocessing, and call ``super().setup()`` from your override if you still
need the default behavior.

``detect()``
~~~~~~~~~~~~

``detect(signals: SignalSet)`` is the only required method. It must accept a
:class:`tsmadkit.signals.SignalSet` and return a
:class:`tsmadkit.AnomalyResult`. The TSM POZ application (C++) calls
``_tsm_poz_execute()`` instead, which wraps ``detect()``; see :doc:`/architecture`.

Populate ``AnomalyResult`` Deliberately
---------------------------------------

``AnomalyResult`` can carry more than a binary decision: ``label``, ``scores``,
``sources``, and ``message`` are all optional context on top of the required
``is_anomaly`` flag. Downstream systems should rely on ``is_anomaly`` as the
primary warning flag, with the other fields treated as contextual metadata.

Use Models Carefully
---------------------

The base setup understands the built-in model sources ``"scikit-learn"``,
``"keras"``, and ``"tensorflow"``, loading ``model.path`` into ``self.model``.
If your algorithm uses a different model format, choose ``"custom"`` as the
source and implement the loading logic yourself in ``setup()``. See the
``model`` section of :doc:`/guides/configuration` for path-resolution rules.

.. _reference-state-example:

Reference-State Example Pattern
--------------------------------

Detectors that compare the current input against historical samples declare a
``reference_state`` (see :doc:`/guides/reference-state` for how that works and
:ref:`reference-state-section` in :doc:`/guides/configuration` for the JSON
keys) and implement ``transform()`` in addition to ``detect()``. If you are
adding a ``reference_state`` for the first time and only have raw ``*.h5``
history samples so far, see :ref:`reference-state-from-scratch`: a single
``setup()`` call bootstraps the manifests, cache, and ``reference_state.json``
from those files.

.. code-block:: python

   import numpy as np

   from tsmadkit import AnomalyDetection, AnomalyResult
   from tsmadkit.signals import SignalSet

   class MyReferenceStateDetector(AnomalyDetection):
       __version__ = "0.1.0"

       def transform(self, data: SignalSet) -> dict:
           # Called once per history sample during setup(), and once for the
           # current sample during detect(). Must return a dict of
           # numpy-savez-compatible arrays with consistent keys/shapes.
           return {"feature": np.mean(data.target_values, axis=-1)}

       def detect(self, signals: SignalSet) -> AnomalyResult:
           current_feature = self.transform(signals)["feature"]
           reference_features = self.cache_data["feature"]

           distance = float(np.linalg.norm(current_feature - reference_features.mean(axis=0)))
           return AnomalyResult(is_anomaly=distance > self.threshold, scores={"distance": distance})

This is the pattern used by algorithms such as
:doc:`../algorithms/generated/ech_collector`.

Testing Discovery
-----------------

After creating the package, verify that the registry can see it:

.. code-block:: bash

   tsmadalg list

or from Python:

.. code-block:: python

   from tsmadalg.tools.registry import get_algorithm_class, list_algorithms

   print(list_algorithms())
   MyAlgorithm = get_algorithm_class("my_algorithm")

If discovery fails, the registry records the error type and error message, and
the CLI shows the message in the ``Details`` column.

A package does not have to live under ``tsmadalg/algorithms`` to be
discovered: list its parent directory in the ``TSMADALG_EXT_PATH``
environment variable (see :doc:`/architecture`) and it is picked up the same
way.

Using the Template Generator
----------------------------

The fastest way to start is ``tsmadalg create my_detector``, which generates
the package skeleton described above. See :doc:`/guides/cli` for the full
list of ``create`` options.

Checklist
---------

Before considering a new algorithm package complete, confirm that:

- the package is located directly under ``tsmadalg/algorithms``
- ``main.py`` defines a detector subclass, re-exported by ``__init__.py``
- ``example_config.json`` validates against the framework schema
- ``detect()`` returns :class:`tsmadkit.AnomalyResult`
- ``setup()`` is called before inference
- ``tsmadalg list`` reports the algorithm as available

Related Pages
-------------

- :doc:`/guides/configuration` for the JSON schema and parameter behavior
- :doc:`/guides/cli` for the CLI that lists and scaffolds algorithms
- :doc:`/algorithms/index` for the generated catalog pages
- :doc:`/api/tsmadkit` for the exact API reference
