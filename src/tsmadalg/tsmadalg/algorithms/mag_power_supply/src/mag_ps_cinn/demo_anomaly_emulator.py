import pandas as pd

from .regular_emulator import RegularEmulator

class DemoAnomalyEmulator(RegularEmulator):
    
    def __init__(self, sim_df: pd.DataFrame):
        super().__init__(sim_df)
        self._measurements, self._labels = self._add_anomalies()

    def measurements(self):
        return self._measurements

    def labels(self):
        return self._labels

    def _add_anomalies(self):
        _coeffs = self.baseline_coeffs()

        name0 = self.output_names[0]
        _coeffs[name0]["b1"] *= 1000.0 

        name1 = self.output_names[1]
        _coeffs[name1]["c1"] *= 5.0 # Increase noise

        df = self._apply_coeffs(_coeffs)

        name2 = self.output_names[2]

        df[name2] *= 1.2

        num_rows = len(df)
        name3 = self.output_names[3]
        df.iloc[num_rows//2 - 5: num_rows//2 + 2] *= 1.3

        return df, self.label_df

