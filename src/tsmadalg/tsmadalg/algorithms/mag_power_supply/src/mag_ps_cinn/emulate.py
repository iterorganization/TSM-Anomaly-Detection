import numpy as np
import pandas as pd


def get_colnames(df: pd.DataFrame, prefix: str) -> list[str]:
    return [n for n in df.columns.values.tolist() if n.startswith(prefix)]

class Emulator:

    def __init__(self, sim_df: pd.DataFrame):

        self.sim_df = sim_df
        self.output_names = get_colnames(self.sim_df, "output")

        # Create a dataframe for labels, which are all initialized
        # to zero (ie no anomaly)
        self.label_df = self.sim_df.copy(deep=True)[self.output_names]
        self.label_df.loc[:,:] = 0



    def baseline_coeffs(self) -> dict:
        rng = np.random.default_rng(12345)

        return {
            name: {
                "a1": rng.normal(loc=0.00007, scale=0.00001),
                "a2": rng.normal(loc=0.0003, scale=0.0001),
                "b1": rng.normal(loc=15, scale=2),
                "c1": rng.uniform(0.5, 1.5),
            }
            for name in self.output_names
        }


    def regular(self):
        _coeffs = self.baseline_coeffs()
        return self._apply_coeffs(_coeffs), self.label_df

    def perturbed(self):
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

    def simple_anomalies(self):

        df, label_df = self.regular()

        num_rows = len(df)
        label_df = self.label_df.copy(deep=True)
        cols = label_df.columns

        rng = np.random.default_rng(1234)
        for name in cols:
           
            # Pick random indices to inject anomalies at
            indices = rng.choice(range(100, num_rows - 100), 25)

            dv_low = 30 
            dv_high = 65 
            perturbation = rng.choice([-1, 1], size=indices.shape) * rng.uniform(dv_low, dv_high, size=indices.shape)

            df[name].iloc[indices] += perturbation
            label_df[name].iloc[indices] = 1

            #label_df[name].iloc[indices] = rng.
            #residual = df[name] - self.sim_df[name]
            #abs_res = np.abs(residual.values)

            #abs_res_indices = np.argsort(abs_res)
            #cond = (abs_res_indices > 10) & (abs_res_indices < num_rows - 10)
            #abs_res_indices = abs_res_indices[cond]

            #for abs_res_index in abs_res_indices[-300::50]:

            #    i_end = abs_res_index + 1
            #    i_start = i_end - 5

            #    residual_multiplier = np.random.choice([-1,1]) * np.random.uniform(0.5, 1)
            #    df[name].iloc[i_end-1] -= (residual_multiplier * residual.iloc[i_end-1])

            #    label_df[name].iloc[i_end-1] = 1

        return df, label_df


    def _apply_coeffs(self, _coeffs: dict) -> pd.DataFrame:
        
        meas_df = self.sim_df.copy(deep=True)
        rng = np.random.default_rng(5678)

        for name, coeffs in _coeffs.items():
            std = np.std(meas_df[name])

            y = meas_df[name]

            dy_dt = np.gradient(y, y.index.values)

            meas_df[name] = (
                y
                - coeffs["a1"] * np.sign(y + coeffs["a2"]) * y**2
                #+ coeffs["b1"] * dy_dt
                + rng.normal(loc=0, scale=coeffs["c1"], size=y.values.shape)
            )

        return meas_df


