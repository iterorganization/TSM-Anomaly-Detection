# ech_collector Synthetic Test

Generate normal pulses as "historical" data, held-out normal pulses as a false-positive baseline, and anomalous pulses as test data.
Then run the `ech_collector` algorithm on both the baseline and anomalous pulses.

## Structure

- `simulation_config.json`: shared simulation settings
- `config.json`: `ech_collector` detector configuration
- `history_config.json`: normal pulse generation for the reference state
- `baseline_config.json`: held-out normal pulse generation for false-positive testing
- `anomalies_config.json`: anomalous pulse generation
- `make_dataset.py`: writes HDF5 pulses into `data/`
- `test_ech_collector.py`: runs `ech_collector` on `data/anomalies/` and `data/baseline/`
- `utils/`: thermal simulation helpers

## Generate Data

Edit `simulation_config.json` for shared simulation settings.
Edit `history_config.json`, `baseline_config.json`, or `anomalies_config.json` for the pulses to generate, then run any of them:

```bash
python make_dataset.py --config history_config.json
python make_dataset.py --config baseline_config.json
python make_dataset.py --config anomalies_config.json
```

Normal pulses are written to `data/history/` as `0001.h5`, `0002.h5`, etc.
Baseline pulses are written to `data/baseline/` the same way, using a different seed so they are not part of the reference-state history.
Anomalous pulses are written to `data/anomalies/` as `0001-a.h5`, `0002-a.h5`, etc.

Like `history_config.json` and `baseline_config.json`, `anomalies_config.json` samples base pulse parameters from bounds rather than listing pulses explicitly.
It additionally has a `faults` section: bounds for each process-level fault type (`cooling_degradation`, `heat_shift`, `heat_fluctuation`, `coolant_ramp`, `radial_resistance_change`), and an `n_faults` range controlling how many faults are injected into each pulse.
A fault bound can be a single `[low, high]` range or a list of ranges, the latter useful to keep a value away from a "no effect" point (e.g. two bands around zero for a rate).

## Run ech_collector

```bash
python test_ech_collector.py --config config.json
```

The script prepares the reference state from `data/history/`, then calls `detect()` on every `*-a.h5` file in `data/anomalies/` and every `*.h5` file in `data/baseline/`.
It displays the number of true positives and false positives.
With the current synthetic dataset, parameter configuration, and algorithm version, it achieves an 86% true-positive rate and a 32% false-positive rate.
Because the dataset is generated randomly, these results should be taken with a grain of salt, although there is likely room to improve both the algorithm and its parameter optimization.
Add `--fail-on-miss` to return a non-zero exit code if any anomalous pulse is not flagged, and `--fail-on-false-positive` to return a non-zero exit code if any baseline pulse is flagged.
