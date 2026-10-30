"""
Write the mag_power_supply detection windows stored in data/data.npz as HDF5 files.

Each window holds the commands (`*_in`), simulated voltages (`*_sim`) and
measured voltages (`*_out`) of every power supply. Baseline windows have no
labeled anomaly; anomalous windows contain at least one synthetic voltage
glitch. The HDF5 files are directly ingestible by the algorithm.
"""

import argparse
from pathlib import Path

import numpy as np

from tsmadkit.io import write_hdf5_input_data

DT = 1e-3


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-file",
        default="data/data.npz",
        help="Path to the *.npz file containing the detection windows.",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Directory to write the 'baseline' and 'anomalies' HDF5 windows into.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    script_dir = Path(__file__).parent

    data_file = Path(args.data_file)
    if not data_file.is_absolute():
        data_file = script_dir / data_file

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    windows = np.load(data_file)
    signal_names = windows["signal_names"].tolist()

    for prefix, suffix in (("baseline", ""), ("anomalies", "-a")):
        target_dir = output_dir / prefix
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in target_dir.glob("*.h5"):
            path.unlink()

        x = windows[f"{prefix}_x"]
        y_sim = windows[f"{prefix}_y_sim"]
        y_meas = windows[f"{prefix}_y_meas"]
        for i in range(len(x)):
            data = make_window_data(x[i], y_sim[i], y_meas[i], signal_names)
            write_hdf5_input_data(target_dir / f"{i + 1:04}{suffix}.h5", data)

        print(f"Wrote {len(x)} windows to {target_dir}")


def make_window_data(x, y_sim, y_meas, signal_names):
    """
    Build a DataDict-shaped payload for one window.
    """
    values = {}
    for i, name in enumerate(signal_names):
        values[f"{name}_in"] = x[i].tolist()
        values[f"{name}_sim"] = y_sim[i].tolist()
        values[f"{name}_out"] = y_meas[i].tolist()

    time = [(k + 1) * DT for k in range(x.shape[-1])]
    return {"time": time, "values": values}


if __name__ == "__main__":
    main()
