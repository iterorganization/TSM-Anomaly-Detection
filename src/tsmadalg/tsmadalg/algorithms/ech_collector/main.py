"""
Intershot anomaly detection for gyrotron collector thermocouples.

This algorithm relies on a configured reference state. The reference state should
be associated with a ``history/`` folder containing past gyrotron pulses in the
expected HDF5 input format; during setup, those pulses are transformed into the
reference distribution used for detection.

Each historical pulse is represented by TSFEL features from the target signals
and the pulse duration derived from the cathode voltage window. At detection
time, the current pulse is transformed in the same way, compared with the
historical reference pulses, decorrelated from pulse duration, reduced with PCA,
and classified with DBSCAN. A pulse is anomalous only when DBSCAN marks it as
noise with label ``-1``.
"""

from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.signals import SignalSet
from tsmadkit.preprocessing import get_above_threshold_window

import tsfel
import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import VarianceThreshold
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors


class ECHCollector(AnomalyDetection):
    """Gyrotron collector intershot anomaly detection."""

    __version__ = "0.0.1"

    def transform(self, data: SignalSet) -> dict[str, np.ndarray | float]:
        """
        Convert one gyrotron pulse into duration and feature data.

        Parameters
        ----------
        data : SignalSet
            Pulse signals on a common time base. The configured cathode voltage
            signal is used to locate the active pulse window, and target signals
            are used for TSFEL feature extraction.

        Returns
        -------
        dict[str, ndarray or float]
            Dictionary containing ``"duration"``, the active pulse duration, and
            ``"features"``, the concatenated TSFEL feature vector for all target
            signals. These values are used for both historical reference pulses
            from the configured reference state and the new pulse under
            investigation.
        """
        # Configure TSFEL for feature extraction
        tsfel_cfg = tsfel.get_features_by_domain(self.domain)

        def feature_extractor(series):
            return tsfel.time_series_features_extractor(
                config=tsfel_cfg,
                timeseries=series,
                fs=self.frequency,
                verbose=0,
            )

        # Determine the active window via threshold crossings of the cathode voltage (Vk)
        cathode_voltage = data[self.Vk_signal]
        (t_start, t_end), _ = get_above_threshold_window(
            time=data.time,
            signal=cathode_voltage,
            time_before=0.0,
            time_after=0.0,
            threshold=self.Vk_threshold,
        )
        pulse_duration = t_end - t_start

        # Extract and concatenate features across all target signals
        pulse_features = np.concatenate([
            feature_extractor(data[signal]).to_numpy().flatten()
            for signal in data.target_names
        ])

        return {"duration": pulse_duration, "features": pulse_features}

    def detect(self, data: SignalSet) -> AnomalyResult:
        """
        Detect whether the current pulse is anomalous relative to reference pulses.

        The new gyrotron pulse and historical reference pulses are standardized,
        filtered by variance, filtered again to remove features correlated with
        pulse duration, projected with PCA, and clustered with DBSCAN. The new
        pulse is considered anomalous only when its DBSCAN label is ``-1``.
        Non-negative labels identify normal cluster membership.

        The anomaly score is ``s(x) = d_k(x) / eps``, where ``x`` is the new
        pulse in reduced feature space, ``d_k(x)`` is its distance to the
        ``k``-th nearest pulse, ``k`` is DBSCAN's ``min_samples`` value, and
        ``eps`` is DBSCAN's neighborhood radius. Values up to ``1`` indicate
        enough local density to be core-like; larger values indicate weaker local
        density and stronger anomaly.

        Parameters
        ----------
        data : SignalSet
            New gyrotron pulse to compare against the historical pulses prepared
            from the configured reference state.

        Returns
        -------
        AnomalyResult
            Detection result with ``is_anomaly`` set from the current pulse's
            DBSCAN label and ``scores["dbscan_isolation_score"]`` containing
            ``s(x)``.
        """
        # Extract features from the current shot
        current = self.transform(data)

        # Compare the current shot with historical reference shots
        features = np.vstack([
            self.cache_data["features"],
            current["features"],
        ])

        durations = np.concatenate([
            self.cache_data["duration"],
            [current["duration"]],
        ])

        # Scaling
        features_scaled = StandardScaler().fit_transform(features)

        # Feature selection: variance threshold
        features_selected = VarianceThreshold(threshold=self.var_threshold).fit_transform(features_scaled)

        # Feature selection: drop features correlated with pulse duration
        duration_correlations = np.abs(np.array([
            spearmanr(features_selected[:, i], durations)[0]
            for i in range(features_selected.shape[1])
        ]))
        features_decorrelated = features_selected[:, duration_correlations < self.spearman_threshold]

        # Dimensionality reduction
        features_reduced = PCA(n_components=self.min_explained_var).fit_transform(features_decorrelated)

        # Clustering
        labels = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit_predict(features_reduced)
        current_label = int(labels[-1])

        # Score s(x) = d_k(x) / eps
        # (d_k(x) is the distance to the k-th neighbor)
        num_samples = len(features_reduced)
        k = min(self.min_samples, num_samples)
        nn = NearestNeighbors(n_neighbors=k)
        nn.fit(features_reduced)
        distances, _ = nn.kneighbors(features_reduced[-1:])
        k_distance = distances[0, -1]
        dbscan_isolation_score = float(k_distance / self.eps)

        return AnomalyResult(
            is_anomaly=current_label == -1,
            scores={"dbscan_isolation_score": dbscan_isolation_score},
        )
