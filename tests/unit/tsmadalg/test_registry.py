import pytest

from tsmadalg.tools.registry import get_algorithm_class, list_algorithms


def test_registry_lists_filters_and_resolves_fake_algorithms(fake_algorithms):
    """Check that registry helpers list, filter, resolve, and reject algorithms correctly."""
    registry = list_algorithms()
    assert registry["fake_algorithm"]["status"] == "available"
    assert registry["fake_algorithm"]["version"] == "1.2.3"
    assert registry["unavailable_algorithm"]["status"] == "unavailable"
    assert registry["unavailable_algorithm"]["error_message"] == "missing optional dependency"

    available = list_algorithms(include_unavailable=False)
    assert "fake_algorithm" in available
    assert "unavailable_algorithm" not in available

    algorithm_class = get_algorithm_class("fake_algorithm")
    assert algorithm_class.__name__ == "FakeAlgorithm"

    with pytest.raises(ValueError, match="Unknown algorithm"):
        get_algorithm_class("missing_algorithm")

    with pytest.raises(ValueError, match="missing optional dependency"):
        get_algorithm_class("unavailable_algorithm")


def test_registry_requires_exactly_one_algorithm_class(fake_algorithms):
    """Check that an algorithm whose main.py defines no AnomalyDetection subclass is unavailable."""
    (fake_algorithms / "no_class_algorithm").mkdir()
    (fake_algorithms / "no_class_algorithm" / "__init__.py").write_text("")
    (fake_algorithms / "no_class_algorithm" / "main.py").write_text("from tsmadkit import AnomalyDetection\n")

    meta = list_algorithms()["no_class_algorithm"]
    assert meta["status"] == "unavailable"
    assert meta["error_type"] == "LookupError"
