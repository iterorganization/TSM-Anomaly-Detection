import numpy as np
import pandas as pd
from scipy.io.matlab import loadmat
import os
import glob

from .paths import DATA_DIR, PS_ONLY_SIM_DIR

def get_ps_only_data_file():
    return os.path.join(PS_ONLY_SIM_DIR, "ps_only_data.mat")

def get_sim_data_file():
    return get_data_files()[0]

def get_data_files():
    query = os.path.join(DATA_DIR, "ps_data_*.mat")
    return glob.glob(query)

def get_split_files(split_dir):
    query = os.path.join(split_dir, "*.mat")
    return glob.glob(query)

def input_output_names(df):
    input_names = [col for col in df.columns if col.startswith('input_')]
    output_names = [col for col in df.columns if col.startswith('output_')]

    return input_names, output_names


def get_inputs(df):
    input_names, _ = input_output_names(df)
    return df[input_names].values.T

def get_outputs(df):
    _, output_names = input_output_names(df)
    return df[output_names].values.T


def read_data_file(filepath, filt=True, transpose=True):

    res = loadmat(filepath)

    times = np.squeeze(res["times"])
    inputs = np.atleast_2d(np.squeeze(res["v_inp"]))
    outputs = np.atleast_2d(np.squeeze(res["v_ps"]))

    # Automatically do transpose based on shape of inputs
    # What we want is inputs.shape[0] to be the time
    # dimension
    transpose = inputs.shape[0] < inputs.shape[1]

    if transpose:
        inputs = inputs.T
        outputs = outputs.T


    _ps_names = res['ps_names']

    if not isinstance(_ps_names[0], str):
        ps_names = [str(el[0]) for el in _ps_names[0, :]]
    else:
        ps_names = _ps_names

    if filt:
        input_names = [f"input_{n}" for n in ps_names if n.strip() != "VS3"]
        output_names = [f"output_{n}" for n in ps_names if n.strip() != "VS3"]
    else:
        input_names = [f"input_{n}" for n in ps_names]
        output_names = [f"output_{n}" for n in ps_names]


    inputs = inputs[:, :len(input_names)]
    outputs = outputs[:, :len(output_names)]

    all_names = input_names + output_names
    all_data = np.hstack([inputs, outputs])

    df = pd.DataFrame(all_data, columns=all_names, index=times*1000.0)
    df.index.name = "times"

    return df


        




