import pytest

from tsmadkit import AnomalyResult
from tsmadkit.io import read_json, write_json

def test_anomaly_result_default_fields():
    """Test that AnomalyResult has correct default field values."""
    anomaly_result = AnomalyResult(is_anomaly=False, scores={"anomaly": 0.95})
    anomaly_result_dict = anomaly_result.to_dict()
    assert anomaly_result_dict["is_anomaly"] is False
    assert anomaly_result_dict["label"] is None
    assert anomaly_result_dict["time_min"] is None
    assert anomaly_result_dict["time_max"] is None
    assert anomaly_result_dict["sources"] is None
    assert anomaly_result_dict["message"] is None

def test_anomaly_result_to_dict(anomaly_result):
    """Test that to_dict correctly converts AnomalyResult to dictionary format."""
    anomaly_result_dict = anomaly_result.to_dict()
    assert anomaly_result_dict == {
        "is_anomaly": True,
        "label": "anomaly",
        "time_min": 1234,
        "time_max": 5678,
        "scores": {"anomaly": 0.95},
        "sources": ["sensor_1", "sensor_2"],
        "details": {"x": 0.234, "y": 0.567},
        "message": "Outlier detected"
    }

def test_anomaly_result_to_json_writes_file(tmp_path, anomaly_result):
    """Test that to_json writes the serialized anomaly result to disk."""
    output_path = tmp_path / "result.json"
    anomaly_result.to_json(output_path)
    assert output_path.exists()
    assert read_json(path=output_path) == anomaly_result.to_dict()

def test_anomaly_result_from_dict(anomaly_result):
    """Test that from_dict reconstructs an AnomalyResult instance."""
    payload = anomaly_result.to_dict()
    anomaly_result_from_dict = AnomalyResult.from_dict(payload)
    assert anomaly_result_from_dict == anomaly_result

def test_anomaly_result_from_json(tmp_path, anomaly_result):
    """Test that from_json reconstructs an AnomalyResult instance from disk."""
    payload = anomaly_result.to_dict()
    input_path = tmp_path / "result.json"
    write_json(payload, path=input_path)
    anomaly_result_from_json = AnomalyResult.from_json(input_path)
    assert anomaly_result_from_json == AnomalyResult(**payload)

def test_anomaly_result_json_round_trip(tmp_path, anomaly_result):
    """Test that AnomalyResult can be serialized to and restored from JSON."""
    original = anomaly_result
    output_path = tmp_path / "result.json"
    original.to_json(output_path)
    restored = AnomalyResult.from_json(output_path)
    assert restored == original
