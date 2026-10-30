"""
Generate normal or anomalous synthetic ECH pulses from a JSON configuration.
"""

import argparse
from pathlib import Path

import numpy as np

from tsmadkit.io import read_json, write_hdf5_input_data

from utils import (
    inject_temperature_anomalies,
    multivariate_normal_sample,
    sample_anomaly_pulses,
    simulate_radial_thermal_lumps,
    step_signal,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the dataset generation configuration JSON.",
    )
    parser.add_argument(
        "--simulation-config",
        help=(
            "Path to the shared simulation configuration JSON. Defaults to "
            "'simulation_config.json' next to --config."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = read_json(config_path)

    # Load shared simulation settings next to the pulse-specific config by default
    simulation_config_path = (
        Path(args.simulation_config).expanduser().resolve()
        if args.simulation_config is not None
        else config_path.with_name("simulation_config.json")
    )
    simulation_config = read_json(simulation_config_path)

    seed = config.get("seed", simulation_config.get("seed"))
    output_dir = Path(config["output_dir"])
    if not output_dir.is_absolute():
        output_dir = config_path.parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if config.get("clean", simulation_config.get("clean", True)):
        for path in output_dir.glob("*.h5"):
            path.unlink()

    # Both normal and anomalous pulses are sampled from bounds
    if "normal" in config:
        pulse_specs = [
            {"parameters": parameters}
            for parameters in multivariate_normal_sample(
                config["normal"]["bounds"],
                n=int(config["normal"]["count"]),
                seed=seed,
            )
        ]
        suffix = ""
    elif "anomalies" in config:
        anomalies = config["anomalies"]
        pulse_specs = sample_anomaly_pulses(
            anomalies["bounds"],
            anomalies["faults"],
            count=int(anomalies["count"]),
            n_faults=tuple(anomalies.get("n_faults", (1, 1))),
            seed=seed,
        )
        suffix = "-a"
    else:
        raise ValueError("Config must define either 'normal' or 'anomalies'.")

    # Keep normal and anomalous file names visually distinct
    files = []
    for pulse_number, spec in enumerate(pulse_specs, start=1):
        pulse_seed = seed + pulse_number if seed is not None else None
        data = make_pulse_data(
            spec["parameters"],
            simulation=simulation_config["simulation"],
            measurement_anomalies=spec.get("measurement_anomalies"),
            seed=pulse_seed,
        )
        path = output_dir / f"{pulse_number:04}{suffix}.h5"
        write_hdf5_input_data(path, data)
        files.append(path)

    print(f"Wrote {len(files)} files to {output_dir}")


def make_pulse_data(parameters, *, simulation, measurement_anomalies=None, seed=None):
    n_thermocouples = int(simulation["n_thermocouples"])
    frequency = float(simulation["frequency"])
    context_signal = simulation.get("context_signal", "ADC1")
    target_signals = simulation.get("target_signals") or [
        f"TT{i:04}" for i in range(1, n_thermocouples + 1)
    ]

    if len(target_signals) != n_thermocouples:
        raise ValueError("target_signals must have one name per thermocouple.")

    # Expand compact scalar configuration values into per-lump arrays
    pulse_parameters = parameters.copy()
    T_init = pulse_parameters.pop("T_0")
    R_radial = pulse_parameters.pop("R_radial")
    R_cooling = pulse_parameters.pop("R_cooling")

    result = simulate_radial_thermal_lumps(
        N=n_thermocouples,
        frequency=frequency,
        T_initial=T_init,
        T_coolant=T_init,
        C=np.full(n_thermocouples, simulation.get("heat_capacity", 30.0)),
        R_radial=np.full(n_thermocouples - 1, R_radial),
        R_cooling=np.full(n_thermocouples, R_cooling),
        **pulse_parameters,
    )

    t = result["t"]
    anomalies = []

    # Baseline measurement noise keeps generated pulses from being perfectly smooth
    noise_std = simulation.get("measurement_noise_std", 0.1)
    if noise_std is not None:
        anomalies.append(
            {
                "type": "noise",
                "t_start": float(t[0]),
                "t_stop": float(t[-1]),
                "std": noise_std,
            }
        )
    anomalies.extend(measurement_anomalies or [])

    temperatures = inject_temperature_anomalies(
        t,
        result["T"],
        anomalies,
        seed=seed,
    )
    voltage = step_signal(
        t_begin=parameters["t_begin"],
        t_end=parameters["t_end"],
        duration=parameters["heat_duration"],
        frequency=frequency,
        amplitude=simulation.get("voltage_amplitude", 50_000.0),
        time=t,
    )

    data = {"time": t.tolist(), "values": {context_signal: voltage.tolist()}}
    for index, signal in enumerate(target_signals):
        data["values"][signal] = temperatures[:, index].tolist()
    return data


if __name__ == "__main__":
    main()
