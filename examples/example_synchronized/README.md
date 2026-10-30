# Content of the folder

This folder contains an implementation of a dummy anomaly detection algorithm using the `AnomalyDetection` class from the `tsmadkit` Python package.

- `algorithm.py`: This file implements the method `detect` in a `DummyLSTMAnomalyDetection` class, which inherits from the abstract `AnomalyDetection` class.

- `config.json`: The configuration file provides information about what signals to read, whether a pre-trained model should be loaded, and algorithm parameters.

- `make_dataset.py`: This module contains functions to generate synthetic signals used to build a dataset for running the dummy synchronized anomaly detection algorithm and test the implementation.

- `lstm_training.ipynb`: A Jupyter notebook to train and save a TensorFlow model of an LSTM for synchronized anomaly detection. The saved model is loaded by the `DummyLSTMAnomalyDetection` class.

- `pipeline_example.ipynb`: A Jupyter notebook showcasing the instantiation and execution of the dummy synchronized anomaly detection algorithm on a synthetic toy dataset. This example demonstrates how to use the implemented algorithm.
