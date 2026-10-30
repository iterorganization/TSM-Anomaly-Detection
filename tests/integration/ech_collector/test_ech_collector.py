"""
Run ECHCollector on generated anomalous and baseline synthetic pulses.
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
        help="Path to the ech_collector detector configuration JSON.",
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
        help="Exit with a non-zero status when any *-a.h5 pulse is not flagged.",
    )
    parser.add_argument(
        "--fail-on-false-positive",
        action="store_true",
        help="Exit with a non-zero status when any baseline pulse is flagged.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Delay heavier imports until execution, so --help stays lightweight
    from tsmadalg.algorithms.ech_collector import ECHCollector

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

    detector = ECHCollector(config_path)

    # Prepare reference history/cache before running detect on anomaly files
    detector.setup()

    anomalous_files = sorted(anomalous_dir.glob("*-a.h5"))
    if not anomalous_files:
        raise FileNotFoundError(f"No anomalous HDF5 files found in {anomalous_dir}")

    baseline_files = sorted(baseline_dir.glob("*.h5"))
    if not baseline_files:
        raise FileNotFoundError(f"No baseline HDF5 files found in {baseline_dir}")

    missed = run_detector(detector, anomalous_files, expected_anomaly=True)
    detected = len(anomalous_files) - len(missed)
    print(f"Detected {detected}/{len(anomalous_files)} anomalous pulses (true positives).")

    false_positives = run_detector(detector, baseline_files, expected_anomaly=False)
    print(f"Flagged {len(false_positives)}/{len(baseline_files)} baseline pulses as anomalous (false positives).")

    if missed and args.fail_on_miss:
        raise SystemExit(f"Missed anomalous pulses: {', '.join(missed)}")

    if false_positives and args.fail_on_false_positive:
        raise SystemExit(f"False positive baseline pulses: {', '.join(false_positives)}")


def run_detector(detector, files, *, expected_anomaly):
    """
    Run detect() on each file and report pulses whose label was not as expected.

    Parameters
    ----------
    detector : AnomalyDetection
        Detector already prepared via setup().
    files : list of Path
        HDF5 pulse files to evaluate.
    expected_anomaly : bool
        Whether these pulses are expected to be flagged as anomalous.

    Returns
    -------
    list of str
        Names of files whose label did not match expected_anomaly.
    """
    from tsmadkit.io import read_hdf5_input_data
    from tsmadkit.signals import SignalSet

    mismatches = []
    for path in files:
        data_dict = read_hdf5_input_data(path)
        data = SignalSet(data_dict, signal_spec=detector.signal_spec)
        result = detector.detect(data)
        score = result.scores.get("dbscan_isolation_score")
        status = "ANOMALY" if result.is_anomaly else "NORMAL"
        print(f"{path.name}: {status} score={score:.3f}")
        if result.is_anomaly != expected_anomaly:
            mismatches.append(path.name)
    return mismatches


if __name__ == "__main__":
    main()
