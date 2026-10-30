# Content of the folder

This folder contains an implementation of a dummy anomaly detection algorithm using the `AnomalyDetection` class from the `tsmadkit` Python package, with a configured reference state for intershot comparison.

- `algorithm.py`: This file implements `DummyClusteringAnomalyDetection`, which extracts TSFEL features from each shot in `transform` and compares the current shot against historical reference shots with PCA and DBSCAN in `detect`.

- `config.json`: The configuration file provides information about what signals to read, algorithm parameters, and the reference state used to store historical shots.

- `make_dataset.py`: This module contains functions to generate and save synthetic single-sensor shots in the HDF5 input-data format expected by `tsmadkit`. Generated shots can populate the reference state's `history/` folder or serve as a new shot for detection.

- `pipeline_example.ipynb`: A Jupyter notebook showcasing the instantiation and execution of the dummy intershot anomaly detection algorithm on a synthetic toy dataset. This example demonstrates how to use the implemented algorithm.
