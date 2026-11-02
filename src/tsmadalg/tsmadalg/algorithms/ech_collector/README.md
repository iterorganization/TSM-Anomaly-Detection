# Gyrotron collector intershot anomaly detection

`ech_collector` is an unsupervised intershot detector for the thermal behavior of a gyrotron collector {cite}`paret_2026_gyrotron`.
It compares a completed pulse with a history of previously observed pulses and flags thermal profiles that lie outside the dense operating regimes represented in that history.
The detector is intended to highlight unusual pulses for review; an outlier is not, by itself, evidence of a physical fault.

## Inputs

Each input represents one complete pulse on a common time grid.

- The target signals are the collector thermocouple time series.
- The context contains the cathode-voltage signal named by `Vk_signal`.
- The cathode voltage must cross `Vk_threshold`, because the interval between its first and last above-threshold samples defines the pulse duration.
- The configured `frequency` must match the sampling frequency of the target data used for feature extraction.

The detector also requires a representative reference history containing pulses with the same target and context signals.
Reference pulses need not have the same duration, but all cache rows must be produced with the same signal configuration and TSFEL feature settings.

## How it works

1. The detector calculates the active pulse duration from the cathode-voltage signal.
2. TSFEL extracts the configured feature domains independently from every target signal, and the features are concatenated into one fixed-length representation of the pulse.
3. The current representation is combined with the cached representations of the reference pulses and standardized.
4. Low-variance features and features whose absolute Spearman correlation with pulse duration exceeds `spearman_threshold` are removed so that the comparison focuses on thermal behavior rather than pulse length.
5. PCA projects the remaining features into the smallest space that retains the fraction of variance selected by `min_explained_var`.
6. DBSCAN groups dense regions in that space, and the current pulse is anomalous only when DBSCAN assigns it the noise label `-1`.

This approach is most sensitive to global changes in the collector heating cycle, such as atypical ramp-up, a missing or distorted plateau, drift, or unusual cool-down behavior.
Short or subtle disturbances confined to one thermocouple can be diluted by the feature aggregation.

## Configuration notes

The example configuration (`example_config.json`) documents the expected gyrotron signals and provides starting preprocessing and DBSCAN values.
The most important settings are:

| Setting                                   | Purpose                                                                             |
| ----------------------------------------- | ----------------------------------------------------------------------------------- |
| `Vk_signal`, `Vk_threshold`           | Select the context signal and threshold used to measure pulse duration.             |
| `frequency`, `domain`                 | Configure TSFEL sampling frequency and feature domains.                             |
| `var_threshold`, `spearman_threshold` | Control feature filtering.                                                          |
| `min_explained_var`                     | Set the fraction of variance retained by PCA when given as a value between 0 and 1. |
| `eps`, `min_samples`                  | Define the DBSCAN neighborhood radius and minimum dense-neighborhood size.          |

`reference_state.path` points to the state file used to track the raw history and its derived feature cache.
On first setup, the conventional paths are `history/manifest.json` and `cache/manifest.json`, relative to the reference-state file.
Place the historical pulses as framework-format `*.h5` files in the corresponding `history/` directory before calling `setup()`.
With `check` set to `full`, setup refreshes the history hashes from those files and rebuilds missing or stale cache entries; `fast` trusts the existing history manifest.

The reference history should cover the normal operating regimes that the detector is expected to accept.
Changing the history or the feature and clustering parameters can change both the DBSCAN classification and the score, so the parameters should be validated against the intended operating data.

## Running the detector

Instantiate the class with a configuration file, call `setup()` once to prepare the reference cache, then call `detect()` for each completed pulse:

```python
from tsmadalg.algorithms.ech_collector import ECHCollector
from tsmadkit.io import read_hdf5_input_data
from tsmadkit.signals import SignalSet

detector = ECHCollector("config.json")
detector.setup()

payload = read_hdf5_input_data("pulse.h5")
signals = SignalSet(payload, detector.signal_spec)
result = detector.detect(signals)

print(result.to_dict())
```

Relative paths in the configuration are resolved from the directory containing the configuration file.

## Result and interpretation

The returned `AnomalyResult` provides:

| Field                                | Meaning                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `is_anomaly`                       | `True` when the current pulse receives DBSCAN label `-1`; otherwise `False`.                     |
| `scores["dbscan_isolation_score"]` | The current pulse's distance to its`min_samples`-th nearest sample in PCA space, divided by `eps`. |

A score at or below `1` means that the current pulse has enough samples within the DBSCAN radius to be core-like.
A larger score indicates greater local isolation, but the Boolean result remains authoritative because a DBSCAN border point can be non-anomalous even when its own score exceeds `1`.

The detector does not return a fault class, a responsible thermocouple, or an anomalous time interval.
Its output should therefore be interpreted as a whole-pulse screening result that calls for inspection of the original signals and operating context.
