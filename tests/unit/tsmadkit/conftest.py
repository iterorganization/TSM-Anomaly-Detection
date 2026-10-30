"""
Pytest configuration and shared fixtures for tsmadkit tests.
"""

import pytest

from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.io import write_hdf5_input_data, write_json
from tsmadkit.signals import SignalSet

@pytest.fixture
def base_config():
    """Provides a valid base configuration dictionary for testing."""
    return {
        "name": "dummy-detector",
        "signals": {
            "targets": ["sensor_0", "sensor_1"],
            "context": ["sensor_2"]},
        "model": None,
        "parameters": {"threshold": 0.5, "sensitivity": 2},
        "anomaly_classes": ["overheating", "arc"],
        "artifacts": ["norm_constants.npz", "scaler.pkl"]
    }

@pytest.fixture
def artifact_files(tmp_path):
    """Create two fake artifiacts in `tmp_path` for a valid base configuration"""
    (tmp_path / "norm_constants.npz").write_text("dummy content")
    (tmp_path / "scaler.pkl").write_text("dummy content")

@pytest.fixture
def base_config_path(tmp_path, base_config, artifact_files):
    """Provides a path to a valid base configuration JSON 
    file with artifacts for testing."""
    path = tmp_path / "config.json"
    write_json(base_config, path=path)
    return path

@pytest.fixture
def data_dict():
    """Provides a sample data dictionary for testing algorithm execution."""
    data_dict = {
        "time": [1.0, 2.0, 3.0],
        "values": {
            "sensor_0":[0.2, 0.4, 0.6],
            "sensor_1":[0.2, 0.4, 0.6],
            "sensor_2":[0.1, 0.3, 0.5]
        }
    }
    return data_dict

@pytest.fixture
def anomaly_result():
    return AnomalyResult(
        is_anomaly=True,
        label="anomaly",
        time_min=1234,
        time_max=5678,
        scores={"anomaly": 0.95},
        sources=["sensor_1", "sensor_2"],
        details={"x": 0.234, "y": 0.567},
        message="Outlier detected"
        )

@pytest.fixture
def dummy_algorithm(base_config_path, anomaly_result):
    """Fixture that creates a dummy AnomalyDetection instance with a valid configuration."""

    # Dummy anomaly detection algorithm
    class DummyDetector(AnomalyDetection):
        __version__ = "0.0.1"

        def detect(self, data):
            return anomaly_result
        
    return DummyDetector(base_config_path)

@pytest.fixture
def signal_set(dummy_algorithm, data_dict):
    """Provides a sample SignalSet for testing algorithm execution"""
    return SignalSet(data_dict, signal_spec=dummy_algorithm.signal_spec)


@pytest.fixture
def reference_state_config(base_config):
    """Provides a configuration dictionary declaring a reference state."""
    config = base_config.copy()
    config.pop("artifacts", None)
    config["reference_state"] = {
        "path": "reference_state.json",
        "check": "fast",
    }
    return config


@pytest.fixture
def reference_state_config_path(tmp_path, reference_state_config):
    """Provides a config file declaring a reference state."""
    path = tmp_path / "config.json"
    write_json(reference_state_config, path=path)
    return path


@pytest.fixture
def reference_history(tmp_path, data_dict):
    """Creates a small HDF5 history directory for reference-state tests."""
    history_dir = tmp_path / "history"
    history_dir.mkdir()

    write_hdf5_input_data(history_dir / "1234.h5", data_dict)

    second = {
        "time": data_dict["time"],
        "values": {
            name: [value + 1.0 for value in values]
            for name, values in data_dict["values"].items()
        },
    }
    write_hdf5_input_data(history_dir / "5678.h5", second)

    return history_dir


@pytest.fixture
def reference_detector_class():
    """Provides a minimal detector that can build reference cache data."""

    class ReferenceDetector(AnomalyDetection):
        __version__ = "0.0.1"

        def transform(self, signals):
            return {
                "sensor_0_mean": signals.value_of("sensor_0").mean(),
                "sensor_1_last": signals.value_of("sensor_1")[-1],
            }

        def detect(self, signals):
            return AnomalyResult(is_anomaly=False)

    return ReferenceDetector
