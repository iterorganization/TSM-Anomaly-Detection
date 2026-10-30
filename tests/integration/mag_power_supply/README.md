# `mag_power_supply` Synthetic Test

Detect anomalies in the magnets power supplies using the `tsmadalg.algorithms.mag_power_supply.MAGPowerSupply` detector, a conditional invertible neural network (cINN).
The test runs the detector on synthetic detection windows stored in `data/data.npz`, some of which contain synthetic voltage glitches.

## Structure

- `config.json`: `mag_power_supply` detector configuration
- `data/data.npz`: 100 baseline and 100 anomalous 10-sample windows (commands, simulated and measured voltages, per-signal anomaly labels)
- `make_dataset.py`: writes the windows of `data/data.npz` as HDF5 files into `data/baseline/` and `data/anomalies/`
- `test_mag_power_supply.py`: runs `mag_power_supply` on `data/anomalies/` and `data/baseline/`
- `cinn.ckpt`, `norms.npz`: trained model checkpoint and input/output normalization constants

## Requirements

- Install the `mag_ps_cinn` package beforehand, following the instructions in `src/tsmadalg/tsmadalg/algorithms/mag_power_supply/src/README.md`.
- The cINN checkpoint's saved hyperparameters point to a relative `norms.npz` path, so `test_mag_power_supply.py` must be run from this folder, where `norms.npz` lives.

## Generate Data

```bash
python make_dataset.py
```

This writes each window of `data/data.npz` into an individual HDF5 file: the 100 windows with no labeled anomaly on any signal go to `data/baseline/`, and the 100 windows with at least one labeled anomalous signal go to `data/anomalies/` with a `-a` suffix.
It only needs `numpy` and `tsmadkit`.

## Run mag_power_supply

```bash
python test_mag_power_supply.py
```

The script loads `config.json`, calls `setup()` to load the cINN checkpoint, then calls `detect()` on every `*.h5` file in `data/baseline/` and `data/anomalies/`, reporting the number of true positives and false positives.

With the current `nll_thresholds`, dataset, and algorithm version, this test achieves a 96% true-positive rate and a 10% false-positive rate.
`config.json`'s `nll_thresholds` were calibrated per signal to maximize each signal's own TPR - FPR trade-off; because a window is flagged whenever *any* signal crosses its own threshold, those individually low per-signal false-positive rates compound into the higher window-level false-positive rate reported above.
Add `--fail-on-miss` to return a non-zero exit code if any anomalous window is not flagged, and `--fail-on-false-positive` to return a non-zero exit code if any baseline window is flagged.
