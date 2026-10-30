# Anomaly detection algorithms

This folder contains toy examples showing how to structure, implement, and run an anomaly detection algorithm with the `tsmadkit` Python package. Each example walks through a different aspect of `tsmadkit`, from configuration and algorithm implementation to reference state management and result inspection. Currently it contains:

- `example_intershot`: a dummy intershot anomaly detection algorithm, illustrating reference state management (`transform`, historical `history/` shots, and cached features).
- `example_synchronized`: a dummy time-resolved anomaly detection algorithm, illustrating model-based detection on a sliding window of signal data.
