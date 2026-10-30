# `tsmadkit` — TSM Anomaly Detection Kit

`tsmadkit` is a lightweight framework for implementing time-series anomaly detection algorithms with a consistent interface. It provides configuration-driven initialization, structured input/output containers, and optional reference-state management, so that an algorithm developer only needs to write the detection logic itself.

The intended developer workflow is small:

1. Create a JSON configuration.
2. Write a subclass of `AnomalyDetection`.
3. Override `setup()` only if needed.
4. Implement `detect()` and, when using reference-state cache data, implement `transform()` too.

## Installing the `tsmadkit` package

Install the `tsmadkit` package locally:

```bash
pip install -e .
```

This will install the core package with its base dependencies. The package is now ready to use within your Python installation.

## Optional Dependencies

To install additional optional dependencies, use extras:

**For development:**
```bash
pip install -e .[dev]
```

**For machine learning model support** (scikit-learn, TensorFlow):
```bash
pip install -e .[ml]
```

**For `AnomalyResult.to_dataframe()` support** (pandas):
```bash
pip install -e .[analysis]
```

**Install multiple optional dependency groups:**
```bash
pip install -e .[ml,dev,analysis]
```

## Core components

- **`AnomalyDetection`**: abstract base class for all anomaly detection algorithms. Subclasses must implement `detect(signals: SignalSet) -> AnomalyResult`.
- **`AnomalyResult`**: a Pydantic model that standardizes the output of anomaly detection algorithms.
- **`SignalSpec`**: immutable signal-role specification loaded from configuration (`targets` + optional `context`).
- **`SignalSet`**: runtime container passed to `detect()`, with a shared time grid and support for multidimensional signals.

## Configuration

Anomaly detection algorithms are configured via JSON files with the following structure:

```json
{
    "name": "my-algorithm",
    "model": {
        "source": "scikit-learn",
        "path": "models/model.joblib"
    },
    "parameters": {
        "parameter_0": 0.5,
        "parameter_1": 2
    },
    "signals": {
        "targets": ["signal_0", "signal_1"],
        "context": ["aux_signal_0"]
    },
    "artifacts": ["additional-data.npz"],
    "anomaly_classes": ["anomaly"],
    "reference_state": {
        "path": "reference_state.json",
        "check": "fast"
    }
}
```

- **`name`**: the name of the algorithm (required).
- **`signals.targets`**: required list of target signal names.
- **`signals.context`**: optional list of contextual signal names (defaults to `[]`). Targets and context must be disjoint.
- **`model`**: (optional) dictionary to load a trained model from disk. Supports scikit-learn, Keras, and TensorFlow formats, or `"custom"`/`null` if the subclass loads the model itself in `setup()`.
- **`parameters`**: (optional) a dictionary of custom algorithm parameters. Each entry becomes an attribute of the algorithm instance.
- **`artifacts`**: (optional) list of additional files needed by the algorithm.
- **`anomaly_classes`**: (optional) list of anomaly class names, used for multiclass detectors.
- **`reference_state`**: (optional) configuration for reference-state tracking, see below.

The configuration is validated against a Pydantic schema (`tsmadkit.config.AlgorithmConfig`). You can validate a configuration ahead of time with `AnomalyDetection.validate_config(config)` or `AnomalyDetection.validate_config_from_json(path)`.

At runtime, the base class exposes the signal split as `self.signal_spec`, and resolves `model.path`/`artifacts` entries to absolute paths (relative paths in the configuration are interpreted relative to the configuration file itself).

## Input data

Input data passed to `detect()` (via a `SignalSet`) or `_tsm_poz_execute()` (via a plain dict) follows a shared-time-grid schema:

```json
{
    "time": [0.0, 0.1, 0.2],
    "values": {
        "signal_0": [1.0, 1.1, 0.9],
        "signal_1": [2.0, 2.1, 2.2],
        "aux_signal_0": [
            [[0, 1], [2, 3]],
            [[4, 5], [6, 7]],
            [[8, 9], [10, 11]]
        ]
    }
}
```

All signals must share the same first axis length as `time`. Trailing dimensions may differ between signals. `tsmadkit.io` provides helpers to read/write this payload as JSON (`read_json_input_data`/`write_json_input_data`) or HDF5 (`read_hdf5_input_data`/`write_hdf5_input_data`).

## Implementing an algorithm

To implement a custom anomaly detection algorithm, create a subclass of `AnomalyDetection`, declare its `__version__`, and implement the `detect()` method:

```python
from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.signals import SignalSet

class MyAnomalyDetection(AnomalyDetection):
    __version__ = "0.1.0"

    def detect(self, signals: SignalSet) -> AnomalyResult:
        # Algorithm logic here
        # Example helpers:
        #   signals.time
        #   signals.target_values
        #   signals.context_values
        #   signals.value_of("signal_name")
        ...
        return AnomalyResult(...)
```

`__version__` is required: instantiating a subclass without it raises a `TypeError`.
Bump it whenever the algorithm's behavior changes, since it is reported with every result and changing it invalidates the reference state cache.

Any additional dependencies your algorithm needs (e.g. `tsfel`, `torch`) can be imported normally at the top of your `main.py`; see [Optional Dependencies](#optional-dependencies) if the dependency should be declared as an extra rather than a core dependency.

## Reference state and caching

Algorithms that need to compare new data against a set of historical samples (rather than a static trained model) can declare a `reference_state` in their configuration. `AnomalyDetection.setup()` then manages, under the reference state's directory:

- `history/manifest.json`: a manifest of raw `*.h5` history samples and their hashes.
- `cache/manifest.json`: a manifest of derived cache files (`*.npz`), one per history sample, built by calling the algorithm's `transform()` method.

To use this feature, implement:

```python
def transform(self, data: SignalSet) -> dict:
    ...
```

The returned dictionary must be serializable with `numpy.savez`, and all cache rows should expose compatible keys/shapes for stacking. The stacked cache data is then available in `detect()` via `self.cache_data`.

The `reference_state.check` mode controls how much work `setup()` does:

- `"fast"`: trust an existing history manifest, and only rebuild missing or stale cache files.
- `"full"`: refresh the history manifest by hashing the actual `*.h5` files, then rebuild only stale or missing cache files (existing valid `.npz` files are left untouched).

Changing the algorithm's name, version, or configuration invalidates the entire cache and triggers a full rebuild on the next `setup()` call.
The configuration is compared through its content hash (`detector.config_hash`), so reformatting the JSON file, passing the same content as a dictionary, or editing the `reference_state` section itself does not count as a change.
