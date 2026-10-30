import numpy as np
from scipy.signal import sawtooth, square


def generate_signal(length: int, sampling_freq: float = 10.0, noise_amplitude: float = 0.1) -> dict:
    """
    Generate a complex periodic signal with added noise.

    Parameters
    ----------
    length : int
        Length of the time series.
    sampling_freq : float, optional
        Sampling frequency of the time series (default is 10.0).
    noise_amplitude : float, optional
        Amplitude of the Gaussian noise (default is 0.1).

    Returns
    -------
    dict
        A dictionary with keys 'time' and 'value', representing the time points and corresponding signal values.
    """

    timestep = 1 / sampling_freq
    t = np.arange(0, length, step=timestep)

    # Creating a mix of periodic functions
    signal = (
        np.sin(t) * np.cos(0.1 * t) +  # Sinusoidal component
        0.2 * sawtooth(0.1 * t) +  # Sawtooth wave component
        0.2 * square(0.1 * t)     # Square wave component
    )

    # Adding Gaussian noise
    noise = noise_amplitude * np.random.normal(size=len(t))
    signal += noise

    return {'time': t, 'value': signal}


def to_sequences(X: np.ndarray, window_size: int) -> tuple:
    """
    Window a dataset into sequences and corresponding target values.

    Parameters
    ----------
    X : np.ndarray
        Input data.
    window_size : int
        Size of the sliding window.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        A tuple containing two NumPy arrays. The first array contains the windowed input data,
        and the second array contains the target values (i.e., the value at the end of each window).
    """
    X_ = []
    y_ = []
    for i in range(len(X)-window_size):
        X_.append(X[i:i+window_size])
        y_.append(X[i+window_size])
    return np.array(X_), np.array(y_)


def to_windowed_payloads(signal: dict, signal_name: str, window_size: int):
    """
    Generator that yields SignalSet-compatible payloads over a sliding window.

    Parameters
    ----------
    signal : dict
        Dictionary with keys 'time' and 'value', as returned by `generate_signal`.
    signal_name : str
        Name to assign to the windowed signal in the payload's ``values``.
    window_size : int
        Number of samples in each window.

    Yields
    ------
    dict
        A ``tsmadkit`` input-data payload with ``"time"`` and ``"values"``
        keys, ready to build a `SignalSet`.
    """
    time_array = np.asarray(signal["time"])
    value_array = np.asarray(signal["value"])

    for i in range(len(time_array) - window_size):
        yield {
            "time": time_array[i:i+window_size].tolist(),
            "values": {signal_name: value_array[i:i+window_size].tolist()},
        }
