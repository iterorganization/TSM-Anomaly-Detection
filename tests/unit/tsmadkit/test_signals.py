import numpy as np
import pytest

from tsmadkit.signals import SignalSet, SignalSpec


@pytest.fixture
def signal_spec(base_config) -> SignalSpec:
    return SignalSpec(
        targets=tuple(base_config["signals"]["targets"]),
        context=tuple(base_config["signals"]["context"]),
    )

def test_signal_spec_basic_properties(signal_spec):
    assert signal_spec.all == ("sensor_0", "sensor_1", "sensor_2")
    assert signal_spec.has_context
    assert signal_spec.is_target("sensor_0")
    assert signal_spec.is_context("sensor_2")
    assert signal_spec.role_of("sensor_1") == "target"
    assert signal_spec.role_of("sensor_2") == "context"
    assert signal_spec.role_of("unknown") is None
    assert list(signal_spec) == ["sensor_0", "sensor_1", "sensor_2"]
    assert "sensor_2" in signal_spec
    assert len(signal_spec) == 3


def test_signal_spec_rejects_overlapping_target_and_context():
    with pytest.raises(ValueError, match="must be disjoint"):
        SignalSpec(targets=("sensor_0",), context=("sensor_0",))


def test_signal_set_basic_structure(data_dict, signal_spec):
    signals = SignalSet(data_dict, signal_spec)

    assert signals.n_samples == 3
    assert signals.n_signals == 3
    assert signals.n_targets == 2
    assert signals.n_context == 1
    assert np.array_equal(signals.names, np.array(["sensor_0", "sensor_1", "sensor_2"]))
    assert np.array_equal(signals.target_names, np.array(["sensor_0", "sensor_1"]))
    assert np.array_equal(signals.context_names, np.array(["sensor_2"]))
    assert signals.has_context

    np.testing.assert_array_equal(signals.time, np.array(data_dict["time"], dtype=np.float64))
    np.testing.assert_array_equal(
        signals.target_values,
        np.array([[0.2, 0.4, 0.6], [0.2, 0.4, 0.6]], dtype=np.float64),
    )
    np.testing.assert_array_equal(
        signals.context_values,
        np.array([[0.1, 0.3, 0.5]], dtype=np.float64),
    )


def test_signal_set_lookup_helpers(data_dict, signal_spec):
    signals = SignalSet(data_dict, signal_spec)

    np.testing.assert_array_equal(signals["sensor_0"], np.array([0.2, 0.4, 0.6], dtype=np.float64))
    np.testing.assert_array_equal(signals.value_of("sensor_1"), np.array([0.2, 0.4, 0.6], dtype=np.float64))
    np.testing.assert_array_equal(
        signals.values_of(["sensor_2", "sensor_0"]),
        np.array([[0.1, 0.3, 0.5], [0.2, 0.4, 0.6]], dtype=np.float64),
    )
    assert signals.index_of("sensor_2") == 2
    assert signals.role_of("sensor_2") == "context"
    assert signals.is_target("sensor_0")
    assert signals.is_context("sensor_2")


def test_signal_set_item_iterators(data_dict, signal_spec):
    signals = SignalSet(data_dict, signal_spec)

    all_items = list(signals.items())
    target_items = list(signals.target_items())
    context_items = list(signals.context_items())

    assert [name for name, _ in all_items] == ["sensor_0", "sensor_1", "sensor_2"]
    assert [name for name, _ in target_items] == ["sensor_0", "sensor_1"]
    assert [name for name, _ in context_items] == ["sensor_2"]


def test_signal_set_from_dict_builds_internal_spec(data_dict, base_config):
    signals = SignalSet.from_dict(
        data_dict,
        targets=base_config["signals"]["targets"],
        context=base_config["signals"]["context"],
    )

    assert signals.signal_spec == SignalSpec(
        targets=tuple(base_config["signals"]["targets"]),
        context=tuple(base_config["signals"]["context"]),
    )


def test_signal_set_equality_on_same_content(data_dict, signal_spec):
    left = SignalSet(data_dict, signal_spec)
    right = SignalSet(data_dict, signal_spec)
    assert left == right


def test_signal_set_equality_handles_nan():
    payload = {
        "time": [0.0, 1.0],
        "values": {
            "sensor_0": [np.nan, 1.0],
        },
    }
    spec = SignalSpec(targets=("sensor_0",), context=())
    left = SignalSet(payload, spec)
    right = SignalSet(payload, spec)
    assert left == right


def test_signal_set_accepts_multidimensional_signals(signal_spec):
    # Simulate 4-frame "video" signals with frame shape (2, 3).
    rng = np.random.default_rng(42)
    video_0 = rng.integers(0, 256, size=(4, 2, 3))
    video_1 = rng.integers(0, 256, size=(4, 2, 3))
    video_2 = rng.integers(0, 256, size=(4, 2, 3))

    payload = {
        "time": [0.0, 1.0, 2.0, 3.0],
        "values": {
            "sensor_0": video_0,
            "sensor_1": video_1,
            "sensor_2": video_2,
        },
    }
    signals = SignalSet(payload, signal_spec)

    assert signals.n_samples == 4
    assert signals.n_signals == 3
    assert signals.values.shape == (3, 4, 2, 3)
    assert signals.target_values.shape == (2, 4, 2, 3)
    assert signals.context_values.shape == (1, 4, 2, 3)

    np.testing.assert_array_equal(signals.value_of("sensor_0"), video_0.astype(np.float64))
    np.testing.assert_array_equal(signals.value_of("sensor_1"), video_1.astype(np.float64))
    np.testing.assert_array_equal(signals.value_of("sensor_2"), video_2.astype(np.float64))


def test_signal_set_accepts_mixed_signal_dimensions(signal_spec):
    rng = np.random.default_rng(123)
    sensor_1d = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float64)
    sensor_video = rng.integers(0, 256, size=(4, 2, 3))
    context_1d = np.array([1.0, 0.0, 1.0, 0.0], dtype=np.float64)

    payload = {
        "time": [0.0, 1.0, 2.0, 3.0],
        "values": {
            "sensor_0": sensor_1d,
            "sensor_1": sensor_video,
            "sensor_2": context_1d,
        },
    }
    signals = SignalSet(payload, signal_spec)

    # Heterogeneous trailing shapes are stored as an object array.
    assert signals.values.dtype == object
    assert signals.values.shape == (3,)
    assert signals.target_values.dtype == object
    assert signals.target_values.shape == (2,)

    np.testing.assert_array_equal(signals.value_of("sensor_0"), sensor_1d)
    np.testing.assert_array_equal(signals.value_of("sensor_1"), sensor_video.astype(np.float64))
    np.testing.assert_array_equal(signals.value_of("sensor_2"), context_1d)

    subset = signals.values_of(["sensor_0", "sensor_1"])
    assert subset.dtype == object
    assert subset.shape == (2,)
    np.testing.assert_array_equal(subset[0], sensor_1d)
    np.testing.assert_array_equal(subset[1], sensor_video.astype(np.float64))
