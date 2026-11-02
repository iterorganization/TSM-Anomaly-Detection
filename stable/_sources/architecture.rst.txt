.. _architecture-guide:

Architecture
============

The repository is intentionally split into a framework package and a catalog
package. This separation keeps the algorithm contract stable while allowing the
set of available algorithms to grow independently.

Package Boundaries
------------------

``tsmadkit`` is the core layer. It contains:

- :class:`tsmadkit.AnomalyDetection`, the base class for all detectors,
  including those that compare against a configured reference state.
- :class:`tsmadkit.AnomalyResult`, the structured output type returned by
  ``detect()``.
- :class:`tsmadkit.signals.SignalSpec` and
  :class:`tsmadkit.signals.SignalSet` for signal-role declarations and runtime
  signal access.
- Configuration validation (:mod:`tsmadkit.config`) and built-in
  model-loading logic.
- Reference-state, history-manifest, and cache-manifest management
  (:mod:`tsmadkit.state`) for detectors that compare against historical
  samples.
- Small preprocessing helpers such as
  :func:`tsmadkit.preprocessing.get_above_threshold_window`.

``tsmadalg`` is the catalog layer. It contains:

- concrete algorithm packages in ``tsmadalg.algorithms``
- automatic discovery of those packages
- a registry with availability metadata
- the ``tsmadalg`` CLI
- the template generator used by ``tsmadalg create``

The packages are therefore related, but they do not have the same
responsibility:

- ``tsmadkit`` defines what an algorithm is.
- ``tsmadalg`` defines which algorithms are currently packaged.

End-to-End Runtime Flow
-----------------------

The typical lifecycle of a detector is:

1. A JSON configuration file (or an equivalent dictionary) is loaded by the
   detector constructor.
2. The configuration is validated against the Pydantic schema
   :class:`tsmadkit.config.AlgorithmConfig`.
3. Core instance attributes such as ``name``, ``signal_spec``, ``parameters``,
   ``model_config``, ``artifacts``, ``anomaly_classes``, and (when configured)
   ``reference_state`` are initialized.
4. The caller invokes ``setup()``.
5. ``detect(signals)`` receives a :class:`tsmadkit.signals.SignalSet` and
   returns an :class:`tsmadkit.AnomalyResult`.

The constructor does not call ``setup()`` automatically. This is deliberate:
model loading and reference-state preparation can be expensive, so the caller
controls when that cost is paid.

Configuration and Instance State
--------------------------------

The configuration file is not just parsed and stored; it is translated into the
runtime state of the detector:

- ``name`` becomes ``self.name``.
- ``signals`` becomes ``self.signal_spec`` (``SignalSpec``), with separated
  ``targets`` and ``context`` roles.
- Each key in ``parameters`` becomes an instance attribute such as
  ``self.threshold`` or ``self.window_size``.
- ``model`` is stored as ``self.model_config`` until ``setup()`` loads the
  actual model into ``self.model``. Its ``path`` entry is normalized to an
  absolute path.
- ``anomaly_classes`` becomes ``self.anomaly_classes``. If the key is omitted,
  the framework defaults to ``["anomaly"]``.
- ``artifacts`` becomes ``self.artifacts`` and can be used by algorithm code to
  locate extra files that are not the main model. Artifact entries are
  normalized to absolute paths.

This is why :doc:`guides/configuration` matters so much: the JSON file directly
defines the runtime surface of the class instance.

Built-In Setup Behavior
-----------------------

The default :meth:`tsmadkit.AnomalyDetection.setup` implementation has two
responsibilities:

- Load the model, when ``model.source`` is one of the built-in loaders.
- Prepare the reference state, when one is configured (see
  :doc:`guides/reference-state` for what that involves).

A ``model.source`` of ``"custom"``, or a configured ``reference_state``
without a ``transform()`` implementation, raises
:class:`NotImplementedError` instead, signaling that the subclass must
perform that setup itself.

Detector Contracts
------------------

Every detector is a subclass of :class:`tsmadkit.AnomalyDetection` and must
implement ``detect(signals)``, receiving the current
:class:`tsmadkit.signals.SignalSet` and returning an
:class:`tsmadkit.AnomalyResult`. Detectors that compare the current input
against historical samples additionally declare a ``reference_state`` and
implement ``transform()``; see :doc:`guides/reference-state` for how that
mechanism works and :doc:`guides/create-algorithm` for a worked example.

Discovery and Registry
----------------------

Each algorithm is imported from its own package (e.g.
``from tsmadalg.algorithms.ech_collector import ECHCollector``), which only imports that
algorithm and its dependencies.

The registry in :mod:`tsmadalg.tools.registry` discovers the algorithm packages
when it is called. It scans the direct subdirectories of
``tsmadalg/algorithms``, plus the algorithm roots listed in the
``TSMADALG_EXT_PATH`` environment variable, and for each package:

1. Creates a registry entry keyed by the directory name.
2. Attempts to import ``tsmadalg.algorithms.<package>.main``.
3. Looks up the :class:`tsmadkit.AnomalyDetection` subclass defined there.
4. Stores metadata such as the algorithm class, version, availability status,
   and import errors.

This is why the algorithm package structure described in
:doc:`guides/create-algorithm` must be respected exactly. The registry is
exposed by two helper functions:

- :func:`tsmadalg.tools.registry.list_algorithms`, which imports all
  algorithms to report their status (used by ``tsmadalg list``)
- :func:`tsmadalg.tools.registry.get_algorithm_class`, which only imports the
  requested algorithm (used by ``tsmadalg run``)

The CLI uses the same registry, so the programmatic and command-line views stay
aligned. See :doc:`guides/cli`.

Algorithm Availability
----------------------

Discovery does not only track successful imports. The registry also keeps
unavailable algorithms and the reason they failed to import, including missing
dependencies or import-time errors in the package.

That behavior is useful for development because:

- the source tree can still contain work-in-progress algorithms
- ``tsmadalg list`` can report missing runtime dependencies
- the documentation can describe an algorithm package even if it is not fully
  importable in the current environment

Generated Algorithm Pages
-------------------------

The pages under :doc:`algorithms/index` are generated automatically at Sphinx
build time from the ``src/tsmadalg/tsmadalg/algorithms`` source tree; see that
page for what each one contains.

How Everything Fits Together
----------------------------

The complete picture is:

- ``tsmadkit`` defines the detector contract and standardized outputs.
- JSON configuration controls how detector instances are initialized.
- ``setup()`` prepares models and optional reference-state/cache data.
- ``detect(signals: SignalSet)`` computes the result for the current input.
- ``tsmadalg`` discovers, catalogs, and scaffolds concrete implementations.

If you want to work from the configuration inward, continue with
:doc:`guides/configuration`. If you want to build a new detector, continue with
:doc:`guides/create-algorithm`.
