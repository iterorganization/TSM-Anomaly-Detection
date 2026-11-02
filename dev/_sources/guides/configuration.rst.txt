.. _configuration-guide:

Configuration Files
===================

Every detector in ``tsmadkit`` is created from a JSON configuration file. That
file is central to the framework: it is validated at construction time and its
contents are translated into runtime attributes on the detector instance.

If you are implementing or packaging an algorithm, treat the configuration file
as part of the public contract of that algorithm.

Minimal Valid Configuration
---------------------------

The base class only requires ``name`` and ``signals``:

.. code-block:: json

   {
       "name": "my-detector",
       "signals": {
           "targets": ["sensor_0", "sensor_1"],
           "context": []
       }
   }

``model``, ``parameters``, ``artifacts``, ``anomaly_classes``, and
``reference_state`` are all optional and default to ``null``/empty when
omitted.

Schema Overview
---------------

The configuration is validated against the Pydantic model
:class:`tsmadkit.config.AlgorithmConfig`. In practical terms, that means:

- the top-level value must be a JSON object
- unknown top-level keys are rejected
- ``name`` and ``signals`` are required
- ``model``, ``parameters``, ``artifacts``, ``anomaly_classes``, and
  ``reference_state`` are optional

Role of Each Entry
------------------

.. list-table::
   :header-rows: 1
   :widths: 18 30 52

   * - Key
     - Accepted values
     - Runtime role
   * - ``name``
     - non-empty string
     - Stored as ``self.name``. This is the human-readable algorithm name carried by the instance.
   * - ``signals``
     - object with required ``targets`` list and optional ``context`` list
     - Stored as ``self.signal_spec`` (:class:`tsmadkit.signals.SignalSpec`) with canonical order ``targets + context``.
   * - ``parameters``
     - object or ``null``
     - Each key/value pair becomes an instance attribute such as ``self.threshold`` or ``self.window_size``.
   * - ``model``
     - ``null`` or an object with ``source`` and ``path``
     - Controls model loading during ``setup()``. The object is first stored as ``self.model_config`` and the loaded model is later stored as ``self.model``.
   * - ``anomaly_classes``
     - optional list of unique non-empty strings
     - Stored as ``self.anomaly_classes``. Used to describe non-normal classes for multiclass or labeled outputs.
   * - ``artifacts``
     - optional list of unique non-empty strings
     - Stored as ``self.artifacts``. Use this for auxiliary files such as normalization constants, scalers, or lookup tables.
   * - ``reference_state``
     - optional object with a ``path`` and an optional ``check`` ("fast" or "full")
     - Stored as ``self.reference_state`` (:class:`tsmadkit.state.ReferenceState`). Enables history/cache management for detectors that compare against historical samples; see :ref:`reference-state-section` below.

Detailed Semantics
------------------

``name``
~~~~~~~~

``name`` is required and must be a non-empty string. It is separate from the
package directory name used by the ``tsmadalg`` registry, so you can choose a
human-oriented value here even if the package name is snake_case.

``signals``
~~~~~~~~~~~

``signals`` defines the names and roles expected in input data:

- ``targets`` is required and must contain at least one signal name.
- ``context`` is optional (defaults to an empty list).
- overlapping names between ``targets`` and ``context`` are rejected.

The base class stores this as ``self.signal_spec`` (a
:class:`tsmadkit.signals.SignalSpec`). Inference code receives a
:class:`tsmadkit.signals.SignalSet`, which follows the same canonical order
(``targets + context``).

``parameters``
~~~~~~~~~~~~~~

``parameters`` is the main customization mechanism for algorithms. Each entry is
copied onto the instance as an attribute.

For example:

.. code-block:: json

   {
       "parameters": {
           "threshold": 0.5,
           "window_size": 64
       }
   }

becomes:

.. code-block:: python

   self.threshold == 0.5
   self.window_size == 64

This behavior is convenient, but it also means parameter names must not collide
with existing instance attributes such as ``name``, ``signal_spec``, ``model``,
or ``setup``. If they do, construction raises :class:`ValueError`.

``model``
~~~~~~~~~

``model`` can be ``null`` if the algorithm does not load a serialized model from
disk. Otherwise it must be an object with:

- ``source``: one of ``"scikit-learn"``, ``"keras"``, ``"tensorflow"``,
  ``"custom"``, or ``null``
- ``path``: a non-empty string

Supported built-in loaders:

- ``"scikit-learn"`` loads the file through ``joblib.load``
- ``"keras"`` loads the file through ``tensorflow.keras.models.load_model``
- ``"tensorflow"`` uses the same TensorFlow loader

Path handling:

- ``model.path`` may be absolute or relative to the JSON configuration file
- when the detector is constructed, ``self.model_config["path"]`` is normalized
  to an absolute path

Important nuance:

- If ``model`` is ``null``, the base ``setup()`` simply skips model loading.
- If ``model.source`` is ``"custom"`` or ``null`` inside a non-null model
  object, the base ``setup()`` raises ``NotImplementedError`` and the subclass
  must implement the loading logic itself.

Relative ``model.path`` values are normalized against the directory containing
the JSON configuration file. Absolute paths are kept as-is.

Example:

.. code-block:: python

   detector = MyDetector("/path/to/config.json")

If ``config.json`` contains:

.. code-block:: json

   {
       "model": {
           "source": "scikit-learn",
           "path": "models/detector.joblib"
       }
   }

then ``detector.model_config["path"]`` becomes:

.. code-block:: python

   "/path/to/models/detector.joblib"

``anomaly_classes``
~~~~~~~~~~~~~~~~~~~

``anomaly_classes`` is optional. If omitted, the framework defaults to:

.. code-block:: python

   ["anomaly"]

The base class also exposes:

- ``self.classes``: ``["OK"] + self.anomaly_classes``
- ``self.is_multiclass``: ``True`` when at least two anomaly classes are defined

These properties help algorithms produce consistent labels and score
dictionaries.

``artifacts``
~~~~~~~~~~~~~

``artifacts`` is optional and meant for files other than the main model. Typical
examples are:

- normalization constants
- scaler objects
- lookup tables
- static metadata needed during inference

The base class stores the list in ``self.artifacts`` and provides
``self.has_artifacts`` as a convenience boolean.

Relative artifact paths are normalized against the directory containing the
JSON configuration file. Absolute paths are kept as-is. At runtime,
``self.artifacts`` contains the resulting absolute paths.

Example:

.. code-block:: python

   detector = MyDetector("/path/to/config.json")

If ``config.json`` contains:

.. code-block:: json

   {
       "artifacts": [
           "artifacts/scaler.joblib",
           "artifacts/reference_statistics.npz"
       ]
   }

then ``detector.artifacts`` becomes:

.. code-block:: python

   [
       "/path/to/artifacts/scaler.joblib",
       "/path/to/artifacts/reference_statistics.npz"
   ]

.. _reference-state-section:

``reference_state``
~~~~~~~~~~~~~~~~~~~~

``reference_state`` is optional and used by detectors that compare the current
input against a set of reference historical samples rather than a static
trained model. This section only covers the JSON keys; see
:doc:`reference-state` for what ``history``/``cache`` mean, how ``setup()``
keeps them in sync depending on ``check``, and how ``transform()`` and
``self.cache_data`` fit in.

.. code-block:: json

   {
       "reference_state": {
           "path": "reference_state.json",
           "check": "fast"
       }
   }

- ``path`` is the location of the reference-state JSON file, resolved the same
  way as ``model.path`` and ``artifacts``.
- ``check`` is ``"fast"`` (default) or ``"full"``.

Conventional bootstrap paths (relative to the reference-state file) are
``history/manifest.json`` and ``cache/manifest.json``; do not declare separate
``history``/``cache`` keys in the algorithm configuration itself.

When configured, the subclass must implement
``transform(self, data: SignalSet) -> dict``.

Complete Example
----------------

.. code-block:: json

   {
       "name": "my-detector",
       "signals": {
           "targets": ["I_plasma", "D_alpha"],
           "context": ["B_tor"]
       },
       "model": {
           "source": "scikit-learn",
           "path": "models/detector.joblib"
       },
       "parameters": {
           "threshold": 0.75
       },
       "anomaly_classes": ["arc", "misfire"],
       "artifacts": [
           "artifacts/scaler.joblib",
           "artifacts/reference_statistics.npz"
       ],
       "reference_state": {
           "path": "reference_state.json",
           "check": "fast"
       }
   }

Validation Helpers
------------------

The framework exposes two validation entry points:

- :meth:`tsmadkit.AnomalyDetection.validate_config` validates a Python
  dictionary
- :meth:`tsmadkit.AnomalyDetection.validate_config_from_json` validates a JSON
  file on disk

That is useful both in tests and in development tools:

.. code-block:: python

   from tsmadkit import AnomalyDetection

   AnomalyDetection.validate_config_from_json("example_config.json")

What Happens After Loading
--------------------------

After successful construction:

- ``self.model`` is initialized to ``None``
- ``self.model_config`` contains the model configuration with an absolute
  ``path`` value, if any
- ``self.artifacts`` contains normalized absolute paths, if any
- ``self.reference_state`` is initialized (its history/cache manifests are
  not yet prepared), if a ``reference_state`` is configured
- the detector is not ready for inference until ``setup()`` has been called

That separation is intentional. Configuration parsing is cheap, while setup may
load large models or additional dependencies.

Configuration and Documentation
-------------------------------

Every packaged algorithm in ``tsmadalg.algorithms`` should ship a meaningful
``example_config.json``. It is not loaded at runtime: it shows what a real
configuration looks like for the algorithm (expected parameters, signal
specifications, whether a model is needed). The Sphinx algorithm pages in
:doc:`/algorithms/index` include that file automatically, so it doubles as
documentation.

Related Runtime Input Shape
---------------------------

Configuration describes which signals are expected; runtime payloads provide
their values. ``_tsm_poz_execute()`` and :mod:`tsmadkit.io` expect:

.. code-block:: json

   {
       "time": [0.0, 0.1, 0.2],
       "values": {
           "sensor_0": [1.0, 1.1, 1.2],
           "sensor_1": [2.0, 2.1, 2.2]
       }
   }

All signals must share the same sample-axis length as ``time``. Signal values
may be multidimensional (for example image/video tensors per sample).

Related Pages
-------------

- :doc:`/guides/create-algorithm` for the implementation side of the detector
  contract
- :doc:`/guides/cli` for scaffolding new algorithms from the command line
- :doc:`/architecture` for the full lifecycle from configuration to execution
