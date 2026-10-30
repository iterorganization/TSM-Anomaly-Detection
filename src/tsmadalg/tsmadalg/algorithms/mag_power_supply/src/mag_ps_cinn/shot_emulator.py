import numpy as np
import matplotlib.pyplot as plt
from .read_data import read_data_file


class ShotEmulator:
    def __init__(self, filepath, rng=None):
        self.filepath = filepath

        self.sim_df = read_data_file(filepath)

        self.output_names = self._get_cols_with_prefix("output")
        self.input_names = self._get_cols_with_prefix("input")

        self.rng = rng or np.random.default_rng(seed=1234)
        self.meas_df = self.sim_df.copy(deep=True)
        self._emulate_meas()

    def _get_cols_with_prefix(self, prefix):
        return [n for n in self.sim_df.columns.values.tolist() if n.startswith(prefix)]

    def _emulate_meas(self):
        for i, name in enumerate(self.output_names):
            std = np.std(self.meas_df[name])

            y = self.meas_df[name]

            dy_dt = np.gradient(y, y.index.values)

            self.meas_df[name] = (
                y
                + 0.00001 * np.sign(y + 0.0001) * y**2
                + 10*dy_dt
                + self.rng.normal(loc=0, scale=0.1 * std, size=y.values.shape)
            )

    def plot_outputs(self):
        prop_cycle = plt.rcParams["axes.prop_cycle"]
        colors = prop_cycle.by_key()["color"]

        fig, axes = plt.subplots(nrows=1, ncols=1, squeeze=False)

        times = self.meas_df.index.values
        for i, name in enumerate(self.output_names):
            (line,) = axes[0][0].plot(times, self.meas_df[name])
            color = line.get_color()
            axes[0][0].plot(times, self.sim_df[name], color=color, ls="dashed")

        plt.show()
