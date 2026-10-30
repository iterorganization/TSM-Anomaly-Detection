import numpy as np

from tsmadkit.io import read_json, write_json
from tsmadkit.signals import SignalSpec
from tsmadkit.state import HistoryState, file_sha256


def test_history_state_read_accepts_signal_spec_override(reference_history):
    history = HistoryState(reference_history / "manifest.json")
    history.update()

    sample = history.read(
        "1234.h5",
        signal_spec=SignalSpec(
            targets=("sensor_0", "sensor_1"),
            context=("sensor_2",),
        ),
    )

    assert sample.target_names.tolist() == ["sensor_0", "sensor_1"]
    assert sample.context_names.tolist() == ["sensor_2"]


def test_setup_bootstraps_reference_state_and_cache(
    reference_detector_class,
    reference_state_config_path,
    reference_history,
):
    detector = reference_detector_class(reference_state_config_path)

    detector.setup()

    assert detector.reference_state.path.is_file()
    assert detector.reference_state.history.path.is_file()
    assert detector.reference_state.cache.path.is_file()
    assert detector.reference_state.hash == file_sha256(detector.reference_state.path)

    cache_data = detector.cache_data
    assert set(cache_data) == {"sensor_0_mean", "sensor_1_last"}
    np.testing.assert_allclose(cache_data["sensor_0_mean"], [0.4, 1.4])
    np.testing.assert_allclose(cache_data["sensor_1_last"], [0.6, 1.6])


def test_setup_accepts_configuration_dict(
    reference_detector_class,
    reference_state_config,
    reference_state_config_path,
    reference_history,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    detector = reference_detector_class(reference_state_config)
    detector.setup()

    state = read_json(detector.reference_state.path)
    assert state["config_hash"] == detector.config_hash

    # The same configuration read from a file reuses the cache
    cache_files = sorted((reference_history.parent / "cache").glob("*.npz"))
    before = {file.name: file.stat().st_mtime_ns for file in cache_files}

    detector = reference_detector_class(reference_state_config_path)
    detector.setup()

    after = {file.name: file.stat().st_mtime_ns for file in cache_files}
    assert after == before


def test_changing_check_mode_does_not_rewrite_cache_files(
    reference_detector_class,
    reference_state_config_path,
    reference_history,
):
    detector = reference_detector_class(reference_state_config_path)
    detector.setup()

    cache_files = sorted((reference_history.parent / "cache").glob("*.npz"))
    before = {file.name: file.stat().st_mtime_ns for file in cache_files}

    config = read_json(reference_state_config_path)
    config["reference_state"]["check"] = "full"
    write_json(config, reference_state_config_path)

    detector = reference_detector_class(reference_state_config_path)
    detector.setup()

    after = {file.name: file.stat().st_mtime_ns for file in cache_files}
    assert after == before


def test_full_check_does_not_rewrite_up_to_date_cache_files(
    reference_detector_class,
    reference_state_config_path,
    reference_history,
):
    config = read_json(reference_state_config_path)
    config["reference_state"]["check"] = "full"
    write_json(config, reference_state_config_path)

    detector = reference_detector_class(reference_state_config_path)
    detector.setup()

    cache_files = sorted((reference_history.parent / "cache").glob("*.npz"))
    before = {file.name: file_sha256(file) for file in cache_files}

    detector = reference_detector_class(reference_state_config_path)
    detector.setup()

    after = {file.name: file_sha256(file) for file in cache_files}
    assert after == before
