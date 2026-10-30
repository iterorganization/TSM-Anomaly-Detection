import json
import sys

import pytest


FAKE_ALGORITHM_MAIN = """\
from tsmadkit import AnomalyDetection, AnomalyResult


class FakeAlgorithm(AnomalyDetection):
    __version__ = "1.2.3"

    def detect(self, signals):
        return AnomalyResult(
            is_anomaly=True,
            label="anomaly",
            scores={"anomaly": float(signals.value_of("signal_a")[-1])},
            sources=["signal_a"],
        )
"""


@pytest.fixture
def fake_algorithms(tmp_path, monkeypatch):
    """Create an available and an unavailable algorithm, discovered through TSMADALG_EXT_PATH."""
    from tsmadalg import algorithms

    root = tmp_path / "algorithms"
    packages = {
        "fake_algorithm": ("from .main import FakeAlgorithm\n", FAKE_ALGORITHM_MAIN),
        "unavailable_algorithm": ("", 'raise ImportError("missing optional dependency")\n'),
    }
    for name, (init_content, main_content) in packages.items():
        (root / name).mkdir(parents=True)
        (root / name / "__init__.py").write_text(init_content)
        (root / name / "main.py").write_text(main_content)

    monkeypatch.setenv("TSMADALG_EXT_PATH", str(root))
    monkeypatch.setattr(algorithms, "__path__", list(algorithms.__path__))
    yield root

    # Forget the imported fake algorithms, so other tests import their own copies
    for module_name in list(sys.modules):
        if module_name.startswith(tuple(f"tsmadalg.algorithms.{name}" for name in packages)):
            del sys.modules[module_name]


@pytest.fixture
def fake_algorithm_config(tmp_path):
    config_path = tmp_path / "fake_algorithm_config.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "fake_algorithm",
                "parameters": {},
                "model": None,
                "signals": {"targets": ["signal_a"], "context": []},
                "anomaly_classes": ["anomaly"],
            }
        )
    )
    return config_path


@pytest.fixture
def input_payload(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps(
            {
                "time": [0.0, 1.0],
                "values": {"signal_a": [0.25, 0.75]},
            }
        )
    )
    return input_path
