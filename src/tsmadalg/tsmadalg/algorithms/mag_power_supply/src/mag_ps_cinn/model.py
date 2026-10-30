import os

import numpy as np
import matplotlib.pyplot as plt
import pytorch_lightning as pl
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from torch.nn.parameter import Parameter
import torchmetrics
# FrEIA imports
import FrEIA.framework as Ff
import FrEIA.modules as Fm

from .paths import (
    MODEL_DIR,
    CHECKPOINT_NAME,
    TRAIN_DIR,
    VAL_DIR,
    TEST_DIR,
    NORM_FILE,
    VIS_DIR,
    PRED_DIR,
    DEMO_PRED_FILE,
    ANOMALY_PRED_FILE,
)
from .read_data import get_split_files, read_data_file
from .regular_emulator import get_colnames, RegularEmulator
from .demo_anomaly_emulator import DemoAnomalyEmulator
from .simple_anomaly_emulator import SimpleAnomalyEmulator


THIS_DIR = os.path.dirname(__file__)
DEFAULT_NORM_FILE = NORM_FILE

DEFAULT_WINDOW_SIZE = 10


################################################################################
# Normalizer
################################################################################


class Normalizer(nn.Module):
    def __init__(self, scale: float, offset: float):
        super().__init__()
        self.scale = Parameter(scale, requires_grad=False)
        self.offset = Parameter(offset, requires_grad=False)

        self.epsilon = 1e-10

    def forward(self, x, signal_index):

        _x = self._transpose(x)
        _x_norm_transpose = (_x - self.offset[signal_index]) / (self.scale[signal_index] + self.epsilon)
        return self._transpose(_x_norm_transpose)


    def _transpose(self, x):
        return x.T

    def inverse(self, x, signal_index):
        _x = self._transpose(x)
        return self._transpose((self.scale[signal_index] * _x) + self.offset[signal_index])



################################################################################
# MetricGroup - Wrap metric in module dict
################################################################################
class MetricGroup(nn.Module):
    def __init__(
        self,
        metric_constructor,
        labels=("train", "val", "test"),
        metric_kwargs: None | dict = None,
        metric_args: None | list = None,
    ):
        super().__init__()

        metric_kwargs = metric_kwargs or {}
        metric_args = metric_args or []

        self._metrics = nn.ModuleDict(
            {
                f"_{label}": metric_constructor(*metric_args, **metric_kwargs)
                for label in labels
            }
        )

    def __getitem__(self, key):
        return self._metrics[f"_{key}"]


################################################################################
# Dataset
################################################################################


class SingleShotDataset(Dataset):
    def __init__(self, filepath, window_size=DEFAULT_WINDOW_SIZE, perturb="regular"):

        assert perturb in ["regular", "anomaly", "demo"]

        self.filepath = filepath
        self.window_size = window_size

        self.sim_df = read_data_file(filepath)

        self.output_names = get_colnames(self.sim_df, "output")
        self.input_names = get_colnames(self.sim_df, "input")

        # Assume for now that the number of inputs is the same
        # as the number of outputs
        assert len(self.input_names) == len(self.output_names)


        if perturb == "demo":
            emulator = DemoAnomalyEmulator(self.sim_df)
        elif perturb == "regular":
            emulator = RegularEmulator(self.sim_df)
        else: # anomaly
            emulator = SimpleAnomalyEmulator(self.sim_df)
            
        self.meas_df = emulator.measurements()
        self.label_df = emulator.labels()

        # Allow catching anomalies within rolling window
        for n in self.output_names:
            vals = self.label_df[n].values
            pos_indices = np.argwhere(vals).reshape(-1)
            for i in pos_indices:
                self.label_df[n].iloc[i:i+self.window_size] = 1


        x_tensor = torch.FloatTensor(self.sim_df[self.input_names].values)
        y_sim_tensor = torch.FloatTensor(self.sim_df[self.output_names].values)
        y_meas_tensor = torch.FloatTensor(self.meas_df[self.output_names].values)
        label_tensor = torch.FloatTensor(self.label_df[self.output_names].values)

        self.x = x_tensor.unfold(0, self.window_size, 1)
        self.y_sim = y_sim_tensor.unfold(0, self.window_size, 1)
        self.y_meas = y_meas_tensor.unfold(0, self.window_size, 1)
        self.labels = label_tensor.unfold(0, self.window_size, 1)



        _n_times = self.x.shape[0]

        self.x = self.x.reshape(-1, self.window_size)
        self.y_sim = self.y_sim.reshape(-1, self.window_size)
        self.y_meas = self.y_meas.reshape(-1, self.window_size)
        self.labels = self.labels.reshape(-1, self.window_size)[:, -1]

        num_signals = len(self.output_names)
        self.signal_indices = torch.arange(num_signals).expand(_n_times, num_signals).reshape(-1)

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

    def __len__(self):
        return self.x.shape[0]

    def __getitem__(self, idx):
        return {
            "x": self.x[idx, ...],
            "y_sim": self.y_sim[idx, ...],
            "y_meas": self.y_meas[idx, ...],
            "signal_indices": self.signal_indices[idx],
            "labels": self.labels[idx],
        }



################################################################################
# Data Module
################################################################################


class PSDataModule(pl.LightningDataModule):
    def __init__(self, batch_size: int = 512, window_size: int = DEFAULT_WINDOW_SIZE, perturb="anomaly"):
        super().__init__()

        self.batch_size = batch_size
        self.window_size = window_size
        self.perturb = perturb

    def setup(self, stage: str):
        ds = self._dataset_from_dir(TRAIN_DIR)

        N = len(ds)
        N_train = int(0.9*N)
        N_val = N - N_train

        self.train_ds, self.val_ds = torch.utils.data.random_split(ds, [N_train, N_val])

        self.test_ds = self._dataset_from_dir(TEST_DIR, perturb="regular")
        self.predict_ds = self._dataset_from_dir(TEST_DIR, perturb=self.perturb)

    def _dataset_from_dir(self, _dir, perturb="regular"):
        files = get_split_files(_dir)
        return ConcatDataset(
            [SingleShotDataset(f, window_size=self.window_size, perturb=perturb) for f in files]
        )

    def train_dataloader(self):
        return DataLoader(self.train_ds, shuffle=True, batch_size=self.batch_size, num_workers=0)

    def val_dataloader(self):
        return DataLoader(self.val_ds, shuffle=False, batch_size=self.batch_size, num_workers=0)


    def test_dataloader(self):
        return DataLoader(self.test_ds, shuffle=False, batch_size=self.batch_size)

    def predict_dataloader(self):
        return DataLoader(self.predict_ds, shuffle=False, batch_size=self.batch_size)


################################################################################
# Can't use short circuit evaluation with tensors, so here's some util functions
# to accomplish the same thing
################################################################################
def _ones_if_none(val, N):
    if val is None:
        val = torch.ones(N)
    return val


def _zeros_if_none(val, N):
    if val is None:
        val = torch.zeros(N)
    return val


################################################################################
# Lightning Module
################################################################################
class PsCINN(pl.LightningModule):
    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        lr: float = 1e-4,
        num_coupling_blocks: int = 8,
        hidden_layer_width: int = 200,
        num_hidden_layers: int = 10,
        norm_file: str = DEFAULT_NORM_FILE,
        pred_file: str = ANOMALY_PRED_FILE, 
    ):
        super().__init__()

        # Calling this saves input kwargs into
        # self.hparams
        self.save_hyperparameters()

        norms_dict = np.load(norm_file)

        self.num_inputs = norms_dict["input_offset"].shape[0]
        self.num_outputs = norms_dict["output_offset"].shape[0]

        self.num_signals = self.num_outputs

        #self.lr = lr


        self.x_normalizer = Normalizer(
            torch.FloatTensor(norms_dict["input_scale"]),
            torch.FloatTensor(norms_dict["input_offset"]),
        )

        self.y_normalizer = Normalizer(
            torch.FloatTensor(norms_dict["output_scale"]),
            torch.FloatTensor(norms_dict["output_offset"]),
        )

        self.nll_group = MetricGroup(torchmetrics.MeanSquaredError)


        self.cond_length = (
            # Inputs
            (self.hparams.window_size - 1)
            # Sim outputs
            + self.hparams.window_size
            # Size of one hot encoded signal index
            + self.num_signals
            # Previous measurements
            #+ (self.hparams.window_size - 1)
        )

        #self.inn = self._create_graph_inn()
        self.inn = self._create_inn()

        self._predictions = []


    def _create_graph_inn(self):

        # we define a subnet for use inside an affine coupling block
        def subnet_fc(dims_in, dims_out):
            print(f"{dims_in=}, {dims_out=}")

            n_layers = self.hparams.num_hidden_layers
            width = self.hparams.hidden_layer_width
            layers = [nn.Linear(dims_in, width), nn.ReLU()]
            for i in range(n_layers-2):
                layers += [nn.Linear(width, width), nn.ReLU()]

            layers += [nn.Linear(width, dims_out)]

            return nn.Sequential(*layers)

        cond = Ff.ConditionNode(self.cond_length, name='Condition') 
        in1 = Ff.InputNode(1, name="In")

        affine = Ff.Node(in1, Fm.AffineCouplingOneSided, {"subnet_constructor": subnet_fc}, conditions=cond, name="Affine Coupling") 
        #affines = []
        #for i in range(self.hparams.num_coupling_blocks):
        #    if i == 0:
        #        upstream = in1
        #    else:
        #        upstream = affine

        #    affine = Ff.Node(upstream, Fm.AffineCouplingOneSided, {"subnet_constructor": subnet_fc}, conditions=cond, name=f"Affine Coupling {i}") 
        #    affines.append(affine)
       
        output = Ff.OutputNode(affine, name='Output 2')

        nodes = [in1, cond, affine, output, ]
        inn = Ff.GraphINN(nodes)

        return inn


    def _create_inn(self):
        # we define a subnet for use inside an affine coupling block
        def subnet_fc(dims_in, dims_out):
            return nn.Sequential(
                nn.Linear(dims_in, self.hparams.hidden_layer_width),
                nn.ReLU(),
                nn.Linear(self.hparams.hidden_layer_width, dims_out),
            )

        # a simple chain of operations is collected by ReversibleSequential
        inn = Ff.SequenceINN(self.hparams.window_size)
        for i in range(self.hparams.num_coupling_blocks):
            inn.append(
                Fm.AllInOneBlock,
                subnet_constructor=subnet_fc,
                cond=0,
                cond_shape=(self.cond_length,),
                permute_soft=True,
            )

        return inn

    def _normalize(self, x: torch.Tensor, y_sim: torch.tensor, y_meas: torch.tensor, ii: torch.tensor):
        return (
            self.x_normalizer(x, ii),
            self.y_normalizer(y_sim, ii),
            self.y_normalizer(y_meas, ii),
        )

    def _process_inputs(
        self, x: torch.Tensor, y_sim: torch.tensor, y_meas: torch.tensor, ii: torch.tensor,
    ):
        _x, _y_sim, _y_meas = self._normalize(x, y_sim, y_meas, ii)

        #_y_meas_latest = _y_meas[:, -1].reshape(-1, 1)
        _y_meas_prev = _y_meas[:, :-1]

        ii_one_hot = torch.nn.functional.one_hot(ii, num_classes=self.num_signals)
        cond = torch.concat([_y_sim, _x[..., :-1], ii_one_hot], dim=-1)

        assert cond.shape[-1] == self.cond_length
        return {
            "y_meas_latest": _y_meas,
            "cond": cond,
        }

    def forward(self, x: torch.Tensor, y_sim: torch.tensor, y_meas: torch.tensor, ii: torch.tensor):
        processed_inputs = self._process_inputs(x, y_sim, y_meas, ii)
        y_meas_latest = processed_inputs["y_meas_latest"]
        cond = processed_inputs["cond"]

        z, log_jac_det = self.inn(y_meas_latest, c=[cond])

        # calculate the negative log-likelihood of the model with a standard normal prior
        nll = 0.5 * torch.sum(z**2, 1) - log_jac_det
        nll = nll/self.hparams.window_size
        return nll

    def inverse(
        self,
        x: torch.Tensor,
        y_sim: torch.Tensor,
        y_meas: torch.Tensor,
        ii: torch.Tensor,
        num_samples: int = 53,
    ):
        processed_inputs = self._process_inputs(x, y_sim, y_meas, ii)
        y_meas_latest = processed_inputs["y_meas_latest"]
        res_lastest = processed_inputs["y_meas_latest"]
        cond = processed_inputs["cond"]

        batch_size = cond.shape[0]

        device = cond.device

        samples = []
        #import pdb; pdb.set_trace()
        for i in range(num_samples):
            # sample from the INN by sampling from a standard normal and transforming
            # it in the reverse direction
            z = torch.randn(batch_size, y_meas_latest.shape[-1], device=device)
            y_meas_hat, _ = self.inn(z, c=[cond], rev=True)
            samples.append(y_meas_hat)

        # shape (num_samples, batch_size, num_outputs)
        y_meas_hats = torch.stack(samples)

        return y_meas_hats

    def _step(self, batch, batch_id, stage):
        x = batch["x"]
        y_sim = batch["y_sim"]
        y_meas = batch["y_meas"]
        signal_indices = batch["signal_indices"]

        nll = self(x, y_sim, y_meas, signal_indices)

        loss = nll.mean()

        if stage != "predict":
            self.log(f"{stage}_loss", loss, prog_bar=True)

        return loss

    def training_step(self, batch, batch_id):
        return self._step(batch, batch_id, "train")

    def validation_step(self, batch, batch_id):
        return self._step(batch, batch_id, "val")

    def test_step(self, batch, batch_id):
        return self._step(batch, batch_id, "test")

    def predict_step(self, batch, batch_id):
        x = batch["x"]
        y_sim = batch["y_sim"]
        y_meas = batch["y_meas"]
        signal_indices = batch["signal_indices"]
        labels = batch["labels"]

        #if batch_id == 50:
        #    y_meas[0, 1, -1] *= 2.0

        y_sim_norm = self.y_normalizer(y_sim, signal_indices)

        y_meas_norm = self.y_normalizer(y_meas, signal_indices)

        y_meas_hat = self.inverse(x, y_sim, y_meas, signal_indices)
        nll = self.forward(x, y_sim, y_meas, signal_indices)

        self._predictions.append(
            {
                "y_meas_hat": y_meas_hat,
                "y_meas": y_meas_norm,
                "y_sim": y_sim_norm,
                "nll": nll,
                "signal_indices": signal_indices,
                "labels": labels,
            }
        )
        return y_meas_hat

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.hparams.lr)

    def on_predict_start(self):
        self._predictions = []

    def on_predict_end(self):
        print("PREDICTION ENDED")

        # Concatenate along batch dimension
        y_meas_hats = [p["y_meas_hat"] for p in self._predictions]
        y_meas_hat = torch.concat(y_meas_hats, dim=1)

        # Each element has shape (batch_size, num_outputs)
        # So, concatenate along dim 0
        y_meass = [p["y_meas"] for p in self._predictions]
        y_meas = torch.concat(y_meass, dim=0)

        y_sims = [p["y_sim"] for p in self._predictions]
        y_sim = torch.concat(y_sims, dim=0)

        nlls = [p["nll"] for p in self._predictions]
        nll = torch.concat(nlls, dim=0)

        labelss = [p["labels"] for p in self._predictions]
        labels = torch.concat(labelss, dim=0)


        iis = [p["signal_indices"] for p in self._predictions]
        ii = torch.concat(iis, dim=0)


        to_save = {
            "y_meas": y_meas.cpu().numpy(),
            "y_meas_hat": y_meas_hat.cpu().numpy(),
            "y_sim": y_sim.cpu().numpy(),
            "nll": nll.cpu().numpy(),
            "signal_indices": ii.cpu().numpy(),
            "num_signals": self.num_signals,
            "labels": labels.cpu().numpy()
        }

        os.makedirs(PRED_DIR, exist_ok=True)
        np.savez(self.hparams.pred_file, **to_save)

        return
