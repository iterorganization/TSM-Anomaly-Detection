import numpy as np

def get_above_threshold_window(
    time: np.ndarray,
    signal: np.ndarray,
    time_before: float = 0.0,
    time_after: float = 0.0,
    threshold: float = 1000,
) -> tuple[tuple[float, float], tuple[int, int]] | None:
    """
    Determine a time window around samples where a signal is above a threshold.

    The returned window spans from the first sample above `threshold` to the
    last sample above `threshold`, optionally padded before and after.

    Padding values are expressed in the same units as `time`.

    Parameters
    ----------
    time : np.ndarray
        1D array of uniformly sampled, sorted time values.
    signal : np.ndarray
        1D array of signal values corresponding to `time`.
    time_before : float, optional
        Amount of time to include before the first above-threshold sample, in
        the same units as `time`. Default is 0.0.
    time_after : float, optional
        Amount of time to include after the last above-threshold sample, in
        the same units as `time`. Default is 0.0.
    threshold : float, optional
        Threshold used to define the above-threshold region. A sample is
        considered above threshold when ``signal > threshold``.
        Default is 1000.

    Returns
    -------
    tuple[tuple[float, float], tuple[int, int]] | None
        ``((tmin, tmax), (imin, imax))`` where:

        - ``tmin`` and ``tmax`` are the start and end values of the padded
          window in the units of `time`.
        - ``imin`` and ``imax`` are the corresponding array indices.

        Returns ``None`` if no samples are above `threshold`.

    Raises
    ------
    ValueError
        If `time` and `signal` do not have the same length.
    """
    if len(time) != len(signal):
        raise ValueError("time and signal arrays must have the same length")

    above = np.where(signal > threshold)[0]

    if above.size == 0:
        return None

    dt = time[1] - time[0]
    pad_before = int(time_before / dt)
    pad_after = int(time_after / dt)

    imin = max(0, above[0] - pad_before)
    imax = min(len(signal) - 1, above[-1] + pad_after)

    return (time[imin], time[imax]), (imin, imax)
