import numpy as np
import pandas as pd
from .regular_emulator import RegularEmulator

class SimpleAnomalyEmulator(RegularEmulator):
    
    def __init__(self, sim_df: pd.DataFrame):
        super().__init__(sim_df)
        self._measurements, self._labels = self._add_anomalies()

    def measurements(self):
        return self._measurements

    def labels(self):
        return self._labels

    def _add_anomalies(self):
        df = super().measurements()
        label_df = super().labels()

        num_rows = len(df)
        cols = label_df.columns

        rng = np.random.default_rng(1234)
        for name in cols:
           
            # Pick random indices to inject anomalies at
            indices = rng.choice(range(num_rows - 25), 25)

            dv_low = 15 
            dv_high = 50
            perturbation = rng.choice([-1, 1], size=indices.shape) * rng.uniform(dv_low, dv_high, size=indices.shape)

            df[name].iloc[indices] += perturbation
            label_df[name].iloc[indices] = 1

        return df, label_df
