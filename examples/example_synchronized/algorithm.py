"""
Synchronized anomaly detection using a pre-trained LSTM.

This algorithm loads a Keras LSTM model at setup time. The LSTM predicts the
next point of a signal from the preceding ``window_size`` points; a sample is
flagged as anomalous when the absolute prediction error exceeds
``abs_error_threshold``.
"""

from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.signals import SignalSet


class DummyLSTMAnomalyDetection(AnomalyDetection):

    __version__ = "0.0.1"

    def detect(self, data: SignalSet) -> AnomalyResult:
        """
        Detect whether the last point of the window is anomalous.

        Parameters
        ----------
        data : SignalSet
            Signal window of ``window_size + 1`` samples: the past
            ``window_size`` points used as LSTM input, followed by the point
            under investigation.

        Returns
        -------
        AnomalyResult
            Detection result with ``is_anomaly`` set when the absolute
            prediction error exceeds ``abs_error_threshold``, and
            ``scores["abs_error"]`` containing that error.
        """
        signal = data["sensor_0"]
        window, actual = signal[:-1], signal[-1]

        prediction = self.model.predict(window.reshape(1, -1, 1), verbose=0)[0, 0]
        abs_error = float(abs(prediction - actual))

        return AnomalyResult(
            is_anomaly=abs_error > self.abs_error_threshold,
            scores={"abs_error": abs_error},
        )
