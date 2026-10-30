# Magnet power-supply anomaly detection

`mag_power_supply` is a model-informed detector for time-localized monitoring of ITER magnet power-supply voltages.
It uses a conditional invertible neural network (CINN) to estimate how likely each measured-voltage window is under the current actuator commands and the voltages predicted by a physics-based model.
This allows deviations to be assessed against regime-dependent expected behavior rather than with a fixed residual limit alone.

## Inputs

Each call processes one synchronized window containing 12 magnet power supplies.
The packaged checkpoint expects exactly 10 samples per signal.

- The 12 target signals are the measured power-supply voltages.
- The first 12 context signals are the corresponding actuator-command windows.
- The next 12 context signals are the corresponding simulated-voltage windows.
- Commands, simulated voltages, and measured voltages must use the same power-supply order shown in the configuration and share one time grid.

The context ordering is part of the current implementation contract because the detector selects the two context groups by position.
For continuous monitoring, the caller should invoke the detector on successive windows of the expected length.

## How it works

1. The detector loads the pretrained CINN and the normalization values used during training.
2. For each power supply, the model conditions on its recent command values, its simulated-voltage window, and the identity of the supply.
3. The CINN maps the measured-voltage window to a standard-normal latent space and evaluates its negative log-likelihood (NLL), including the transformation Jacobian.
4. The NLL for each supply is compared with the threshold at the same position in `nll_thresholds`.
5. The window is anomalous when at least one supply exceeds its threshold.

Higher NLL means that a measured-voltage window is less likely under the operating conditions learned by the model.
The implementation uses the CINN's forward likelihood for detection; it does not return reconstructed voltage traces or uncertainty bands.

## Configuration notes

The example configuration (`example_config.json`) defines the required ordering of the 12 command signals, 12 simulated voltages, and 12 measured voltages.
The most important settings and resources are:

| Setting or resource | Purpose |
| --- | --- |
| `model.path` | Points to the trained cINN checkpoint (e.g. `cinn.ckpt`) loaded during `setup()`. |
| `artifacts` | Lists the normalization constants file (e.g. `norms.npz`) the checkpoint was trained with. |
| `device` | Selects the PyTorch inference device; the example configuration uses `cpu`. |
| `nll_thresholds` | Contains one decision threshold per target, in exactly the same order as `signals.targets`. |

A trained cINN checkpoint and its normalization constants are currently required to run the algorithm, and must be available before calling `setup()`.
They are not shipped with this package.
The checkpoint stores the normalization constants file as a relative path, so the process must be launched with that file available at the checkpoint's stored path.

> **Warning:** `tsmadalg` cannot train the cINN yet.
> A planned refactoring of the `mag_ps_cinn` package will allow (re)training the cINN directly from `tsmadalg`.
Thresholds are model- and signal-specific and should be calibrated on representative nominal and anomalous windows rather than interpreted as probabilities.

## Running the detector

Instantiate the class with a configuration file, call `setup()` once to load the CINN, then call `detect()` for each input window:

```python
import numpy as np

from tsmadalg.algorithms.mag_power_supply import MAGPowerSupply
from tsmadkit.io import read_json_input_data
from tsmadkit.signals import SignalSet

detector = MAGPowerSupply("config.json")
detector.setup()

payload = read_json_input_data("window.json")
signals = SignalSet(payload, detector.signal_spec, dtype=np.float32)
result = detector.detect(signals)

print(result.to_dict())
```

Using `float32` input matches the packaged PyTorch checkpoint.
Relative paths in the configuration are resolved from the directory containing the configuration file.

## Result and interpretation

The returned `AnomalyResult` provides:

| Field | Meaning |
| --- | --- |
| `is_anomaly` | `True` when at least one per-supply NLL exceeds its configured threshold. |
| `scores["max_nll"]` | The largest NLL across the 12 monitored supplies in the input window. |
| `sources` | The measured-voltage signal names whose NLL values exceeded their respective thresholds, or `None` for a normal window. |

`max_nll` is a continuous summary of the least-likely channel, while `is_anomaly` and `sources` reflect the configured per-channel thresholds.
The result identifies affected power supplies at window resolution, but it does not identify an exact sample within the window or classify the underlying fault.
It should be treated as a model-consistency warning and reviewed together with the measured signals, simulated signals, and operating context.
