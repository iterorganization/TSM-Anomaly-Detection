"""
Run mag_power_supply on generated anomalous and baseline synthetic detection windows.
"""

import argparse
from pathlib import Path


# Pytest will not collect this as a test
__test__ = False


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the mag_power_supply detector configuration JSON.",
    )
    parser.add_argument(
        "--data-root",
        default="data",
        help="Directory containing generated synthetic data.",
    )
    parser.add_argument(
        "--anomalous-dir",
        default="anomalies",
        help="Subdirectory under data-root containing *-a.h5 files.",
    )
    parser.add_argument(
        "--baseline-dir",
        default="baseline",
        help="Subdirectory under data-root containing normal *.h5 files.",
    )
    parser.add_argument(
        "--fail-on-miss",
        action="store_true",
        help="Exit with a non-zero status when any *-a.h5 window is not flagged.",
    )
    parser.add_argument(
        "--fail-on-false-positive",
        action="store_true",
        help="Exit with a non-zero status when any baseline window is flagged.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    config_path = Path(args.config).expanduser().resolve()
    data_root = Path(args.data_root)
    if not data_root.is_absolute():
        data_root = config_path.parent / data_root

    anomalous_dir = Path(args.anomalous_dir)
    if not anomalous_dir.is_absolute():
        anomalous_dir = data_root / anomalous_dir

    baseline_dir = Path(args.baseline_dir)
    if not baseline_dir.is_absolute():
        baseline_dir = data_root / baseline_dir

    # Delay heavier imports until execution, so --help stays lightweight
    from tsmadalg.algorithms.mag_power_supply import MAGPowerSupply

    detector = MAGPowerSupply(config_path)
    detector.setup()

    anomalous_files = sorted(anomalous_dir.glob("*-a.h5"))
    if not anomalous_files:
        raise FileNotFoundError(f"No anomalous HDF5 files found in {anomalous_dir}")

    baseline_files = sorted(baseline_dir.glob("*.h5"))
    if not baseline_files:
        raise FileNotFoundError(f"No baseline HDF5 files found in {baseline_dir}")

    missed = run_detector(detector, anomalous_files, expected_anomaly=True)
    detected = len(anomalous_files) - len(missed)
    print(f"Detected {detected}/{len(anomalous_files)} anomalous windows (true positives).")

    false_positives = run_detector(detector, baseline_files, expected_anomaly=False)
    print(f"Flagged {len(false_positives)}/{len(baseline_files)} baseline windows as anomalous (false positives).")

    if missed and args.fail_on_miss:
        raise SystemExit(f"Missed anomalous windows: {', '.join(missed)}")

    if false_positives and args.fail_on_false_positive:
        raise SystemExit(f"False positive baseline windows: {', '.join(false_positives)}")


def run_detector(detector, files, *, expected_anomaly):
    """
    Run detect() on each file and report windows whose label was not as expected.

    Parameters
    ----------
    detector : AnomalyDetection
        Detector already prepared via setup().
    files : list of Path
        HDF5 detection windows to evaluate.
    expected_anomaly : bool
        Whether these windows are expected to be flagged as anomalous.

    Returns
    -------
    list of str
        Names of files whose label did not match expected_anomaly.
    """
    import numpy as np

    from tsmadkit.io import read_hdf5_input_data
    from tsmadkit.signals import SignalSet

    mismatches = []
    for path in files:
        data_dict = read_hdf5_input_data(path)
        # The cINN checkpoint's weights are float32, so signals must match
        data = SignalSet(data_dict, signal_spec=detector.signal_spec, dtype=np.float32)
        result = detector.detect(data)
        score = result.scores.get("max_nll")
        status = "ANOMALY" if result.is_anomaly else "NORMAL"
        source = f" source={result.sources}" if result.sources else ""
        print(f"{path.name}: {status} score={score:.3f}{source}")
        if result.is_anomaly != expected_anomaly:
            mismatches.append(path.name)
    return mismatches


if __name__ == "__main__":
    main()
