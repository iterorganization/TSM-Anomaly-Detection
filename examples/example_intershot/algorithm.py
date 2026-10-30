"""
Intershot anomaly detection using per-shot TSFEL features.

This algorithm relies on a configured reference state. The reference state
should be associated with a ``history/`` folder containing past shots in the
expected HDF5 input format; during setup, those shots are transformed into
TSFEL feature vectors used as the reference distribution for detection.

At detection time, the current shot is transformed the same way, combined
with the historical feature vectors, scaled, reduced with PCA, and clustered
with DBSCAN. A shot is anomalous only when DBSCAN marks it as noise with
label ``-1``.
"""

from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.signals import SignalSet

import tsfel
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors


class DummyClusteringAnomalyDetection(AnomalyDetection):

    __version__ = "0.0.1"

    def transform(self, data: SignalSet) -> dict[str, np.ndarray]:
        """
        Extract TSFEL features from one shot.

        Parameters
        ----------
        data : SignalSet
            Shot signal on its own time base.

        Returns
        -------
        dict[str, ndarray]
            Dictionary containing ``"features"``, the TSFEL feature vector for
            the configured target signal. Used for both historical reference
            shots from the configured reference state and the new shot under
            investigation.
        """
        tsfel_cfg = tsfel.get_features_by_domain(self.domain)
        features = tsfel.time_series_features_extractor(
            config=tsfel_cfg,
            timeseries=data["sensor_0"],
            fs=self.frequency,
            verbose=0,
        ).to_numpy().flatten()
        return {"features": features}

    def detect(self, data: SignalSet) -> AnomalyResult:
        """
        Detect whether the current shot is anomalous relative to reference shots.

        The new shot and historical reference shots are standardized, projected
        with PCA, and clustered with DBSCAN. The new shot is considered
        anomalous only when its DBSCAN label is ``-1``. Non-negative labels
        identify normal cluster membership.

        The anomaly score is ``s(x) = d_k(x) / eps``, where ``x`` is the new
        shot in reduced feature space, ``d_k(x)`` is its distance to the
        ``k``-th nearest shot, ``k`` is DBSCAN's ``min_samples`` value, and
        ``eps`` is DBSCAN's neighborhood radius. Values up to ``1`` indicate
        enough local density to be core-like; larger values indicate weaker
        local density and stronger anomaly.

        Parameters
        ----------
        data : SignalSet
            New shot to compare against the historical shots prepared from the
            configured reference state.

        Returns
        -------
        AnomalyResult
            Detection result with ``is_anomaly`` set from the current shot's
            DBSCAN label and ``scores["dbscan_isolation_score"]`` containing
            ``s(x)``.
        """
        current = self.transform(data)

        features = np.vstack([self.cache_data["features"], current["features"]])
        features_scaled = StandardScaler().fit_transform(features)
        features_reduced = PCA(n_components=self.n_components).fit_transform(features_scaled)

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
