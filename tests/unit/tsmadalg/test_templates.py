import json

from tsmadalg.tools.templates import generate_algorithm_template


def test_generate_algorithm_template_creates_expected_files(tmp_path):
    """Check that template generation creates the expected files and base classes."""
    algorithm_dir = generate_algorithm_template(
        "DemoDetector",
        version="1.2.0",
        parameters={"threshold": 0.4},
        anomaly_classes=["spike"],
        target_signals=["signal_a"],
        context_signals=["ambient"],
        output_dir=tmp_path,
    )

    assert algorithm_dir == tmp_path / "demo_detector"
    assert (algorithm_dir / "__init__.py").read_text() == "from .main import DemoDetector\n"

    main_py = (algorithm_dir / "main.py").read_text()
    assert "class DemoDetector(AnomalyDetection):" in main_py
    assert '__version__ = "1.2.0"' in main_py

    config = json.loads((algorithm_dir / "example_config.json").read_text())
    assert config == {
        "name": "DemoDetector",
        "parameters": {"threshold": 0.4},
        "signals": {"targets": ["signal_a"], "context": ["ambient"]},
        "anomaly_classes": ["spike"],
    }

    intershot_dir = generate_algorithm_template(
        "HistoricalDetector",
        output_dir=tmp_path,
    )
    intershot_main_py = (intershot_dir / "main.py").read_text()
    assert "class HistoricalDetector(AnomalyDetection):" in intershot_main_py

