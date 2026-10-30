"""
Utilities for generating synthetic ECH anomaly-detection datasets.
"""

from .simulation import (
    inject_temperature_anomalies,
    multivariate_normal_sample,
    sample_anomaly_pulses,
    simulate_radial_thermal_lumps,
    step_signal,
)
