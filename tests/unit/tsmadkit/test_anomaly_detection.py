import copy
import json
import pytest

from tsmadkit import AnomalyDetection
from tsmadkit.config import AlgorithmConfig
from pydantic import ValidationError

def test_validate_config_accepts_valid_config(base_config):
    """Test that validate_config accepts a valid configuration."""
    # Should not raise
    AnomalyDetection.validate_config(base_config)

def test_validate_config_from_json(tmp_path, base_config):
    """Test that validate_config_from_json accepts a valid JSON configuration file."""
    cfg_json = tmp_path / "valid_config.json"
    cfg_json.write_text(json.dumps(base_config))
    # Should not raise
    AnomalyDetection.validate_config_from_json(cfg_json)

def test_validate_config_accepts_missing_anomaly_classes(base_config):
    """Test that validate_config accepts configurations without anomaly_classes."""
    cfg = copy.deepcopy(base_config)
    cfg.pop("anomaly_classes", None)
    AnomalyDetection.validate_config(cfg)  # should not raise

@pytest.mark.parametrize(
    "mutator",
    [
        # Missing required keys
        (lambda c: (c.pop("name"), c)[1]),
        (lambda c: (c.pop("signals"), c)[1]),
        # 'name' wrong type
        (lambda c: {**c, "name": 123}),
        # 'name' empty string
        (lambda c: {**c, "name": ""}),
        # 'signals' wrong type
        (lambda c: {**c, "signals": "not-a-list"}),
        # 'signals' empty
        (lambda c: {**c, "signals": []}),
        # 'model' wrong type (must be object or null)
        (lambda c: {**c, "model": "not-a-dict"}),
        # 'model' object missing required 'path'
        (lambda c: {**c, "model": {"source": "scikit-learn"}}),
        # 'model.source' unknown
        (lambda c: {**c, "model": {"source": "pytorch", "path": "m.ckpt"}}),
        # 'parameters' wrong type (must be object or null)
        (lambda c: {**c, "parameters": 42}),
        # anomaly_classes: all invalid if present
        (lambda c: {**c, "anomaly_classes": "not-a-list"}),        # wrong type
        (lambda c: {**c, "anomaly_classes": [1, 2]}),              # non-strings
        (lambda c: {**c, "anomaly_classes": ["", "arc"]}),         # empty string
        (lambda c: {**c, "anomaly_classes": ["arc", "arc"]}),      # duplicates
        # artifacts: invalid cases
        (lambda c: {**c, "artifacts": "not-a-list"}),              # wrong type
        (lambda c: {**c, "artifacts": ["", "file2.npz"]}),         # empty string
        (lambda c: {**c, "artifacts": ["file1.npz", "file1.npz"]}) # duplicates
    ],
)
def test_validate_config_rejects_invalid_configs(mutator, base_config):
    """Test that validate_config rejects invalid configurations."""
    bad_cfg = mutator(copy.deepcopy(base_config))
    with pytest.raises(ValidationError):
        AnomalyDetection.validate_config(bad_cfg)

def test_initialization_and_parameters(dummy_algorithm, tmp_path):
    """Test that algorithm initialization correctly sets name, signals, parameters, and artifacts."""
    assert dummy_algorithm.name == "dummy-detector"
    assert set(dummy_algorithm.signal_spec.all) == set(["sensor_0", "sensor_1", "sensor_2"])
    assert dummy_algorithm.parameters == {"threshold": 0.5, "sensitivity": 2}
    assert dummy_algorithm.threshold == 0.5
    assert dummy_algorithm.sensitivity == 2
    assert dummy_algorithm.has_artifacts
    assert dummy_algorithm.artifacts == [
        str(tmp_path / "norm_constants.npz"),
        str(tmp_path / "scaler.pkl")
        ]

def test_initialization_accepts_configuration_dict(
    base_config,
    artifact_files,
    tmp_path,
    monkeypatch,
):
    """Test that an algorithm can be initialized from a configuration dictionary."""
    monkeypatch.chdir(tmp_path)

    class DummyDetector(AnomalyDetection):
        __version__ = "0.0.1"

        def detect(self, data):
            return None

    detector = DummyDetector(base_config)

    assert detector.name == "dummy-detector"

@pytest.mark.parametrize("version", [None, "", 1])
def test_initialization_requires_version(base_config_path, version):
    """Test that an algorithm without a valid __version__ cannot be instantiated."""

    class UnversionedDetector(AnomalyDetection):
        def detect(self, data):
            return None

    if version is not None:
        UnversionedDetector.__version__ = version

    with pytest.raises(TypeError, match="__version__"):
        UnversionedDetector(base_config_path)

def test_config_hash_does_not_depend_on_configuration_source(
    dummy_algorithm,
    base_config,
    tmp_path,
    monkeypatch,
):
    """Test that a file and a dictionary with the same content have the same hash."""
    monkeypatch.chdir(tmp_path)
    detector = type(dummy_algorithm)(base_config)

    assert detector.config_hash == dummy_algorithm.config_hash

def test_config_hash_ignores_reference_state_only(base_config):
    """Test that the hash ignores the reference_state section but not the rest."""
    config = copy.deepcopy(base_config)
    reference = AlgorithmConfig.model_validate(config).sha256()

    config["reference_state"] = {"path": "reference_state.json", "check": "full"}
    assert AlgorithmConfig.model_validate(config).sha256() == reference

    config["parameters"]["threshold"] = 0.6
    assert AlgorithmConfig.model_validate(config).sha256() != reference

def test_tsm_poz_execute(dummy_algorithm, data_dict):
    """Test that _tsm_poz_execute returns correct anomaly detection results."""
    is_anomaly, scores, details, anomaly_result_str = dummy_algorithm._tsm_poz_execute(data_dict)
    reference = {
        "algorithm_name": "dummy-detector",
        "algorithm_version": "0.0.1",
        "config_hash": dummy_algorithm.config_hash,
        "reference_state_hash": None,
        "details": {"x": 0.234, "y": 0.567},
        "is_anomaly": True,
        "label": "anomaly",
        "message": "Outlier detected",
        "scores": {"anomaly": 0.95},
        "sources": ["sensor_1", "sensor_2"],
        "time_max": 5678,
        "time_min": 1234,
    }
    assert is_anomaly is True
    assert scores == {"anomaly": 0.95}
    assert details == '{"x": 0.234, "y": 0.567}'
    assert json.loads(anomaly_result_str) == reference
