"""
Generate synthetic single-sensor shots for the intershot anomaly detection example.
"""

import numpy as np

from tsmadkit.io import write_hdf5_input_data


def generate_signal(
    length: int,
    signal_frequency: float = 1.0,
    sampling_freq: float = 100.0,
    noise_amplitude: float = 0.10,
) -> dict:
    """
    Generate a sinusoidal time series with Gaussian noise.

    Parameters
    ----------
    length : int
        Length of the time series.
    signal_frequency : float, optional
        Frequency of the sinusoidal signal (default is 1.0).
    sampling_freq : float, optional
        Sampling frequency of the time series (default is 100.0).
    noise_amplitude : float, optional
        Amplitude of the Gaussian noise (default is 0.10).

    Returns
    -------
    dict
        A ``tsmadkit`` input-data payload with ``"time"`` and ``"values"``
        keys, the latter containing the ``"sensor_0"`` signal.
    """
    timestep = 1 / sampling_freq
    time = np.arange(0, length, step=timestep)
    value = np.sin(2 * np.pi * signal_frequency * time) + noise_amplitude * np.random.normal(size=len(time))
    return {"time": time.tolist(), "values": {"sensor_0": value.tolist()}}
