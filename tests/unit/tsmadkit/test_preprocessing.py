from tsmadkit.preprocessing import get_above_threshold_window
import numpy as np

def test_get_above_threshold_window():
    time = np.arange(0.0, 1.0, 0.1)
    signal = np.array([0, 0, 11, 12, 13, 0, 0, 15, 16, 0])

    result = get_above_threshold_window(
        time=time,
        signal=signal,
        threshold=10,
        time_before=0.1,
        time_after=0.2,
    )

    assert result == (
        (0.1, 0.9),
        (1, 9),
    )