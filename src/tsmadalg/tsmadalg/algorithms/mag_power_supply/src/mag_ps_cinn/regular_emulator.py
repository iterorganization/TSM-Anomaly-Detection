import numpy as np
import pandas as pd

def get_colnames(df: pd.DataFrame, prefix: str) -> list[str]:
    return [n for n in df.columns.values.tolist() if n.startswith(prefix)]

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

class RegularEmulator:

    def __init__(self, sim_df: pd.DataFrame):

        self.sim_df = sim_df
        self.output_names = get_colnames(self.sim_df, "output")

        # Create a dataframe for labels, which are all initialized
        # to zero (ie no anomaly)
        self._label_df = self.sim_df.copy(deep=True)[self.output_names]
        self._label_df.loc[:,:] = 0

    def measurements(self):
        _coeffs = self.baseline_coeffs()
        return self._apply_coeffs(_coeffs)

    def labels(self):
        return self._label_df

    def baseline_coeffs(self) -> dict:
        rng = np.random.default_rng(12345)

        return {
            name: {
                "a1": rng.normal(loc=0.0003, scale=0.00005),
                "b1": rng.normal(loc=1, scale=0.25),
                "c1": rng.uniform(0.5, 1.5),
            }
            for name in self.output_names
        }

    def _apply_coeffs(self, _coeffs: dict) -> pd.DataFrame:
        
        meas_df = self.sim_df.copy(deep=True)
        rng = np.random.default_rng(5678)

        for name, coeffs in _coeffs.items():
            std = np.std(meas_df[name])

            y = meas_df[name]

            dy_dt = np.gradient(y, y.index.values)
            
            print("*"*80)
            print(name)
            print(coeffs)

            perturb_a1 = 0.2*sigmoid(coeffs["a1"]*np.abs(y))
            perturb_b1 = 0.2*sigmoid(coeffs["b1"]*np.abs(dy_dt))

            #fig, ax = plt.subplots()
            #sns.kdeplot(perturb_a1, ax=ax)
            #fig.suptitle("a1")

            #fig, ax = plt.subplots()
            #sns.kdeplot(perturb_b1, ax=ax)
            #fig.suptitle("b1")
            #import pdb; pdb.set_trace()

            meas_df[name] = (
                y * (1 + perturb_a1 + perturb_b1)
                + rng.normal(loc=0, scale=coeffs["c1"], size=y.values.shape)
            )
        return meas_df

