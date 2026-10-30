import os

THIS_FILE = os.path.realpath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)
PROJECT_ROOT = os.path.realpath(os.path.join(THIS_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "sim")

INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "ps_inputs")
INPUT_FILE = os.path.join(INPUT_DIR, "ps_inputs.mat")

SPLITS_DIR = os.path.join(PROJECT_ROOT, "data", "splits")

TRAIN_DIR = os.path.join(SPLITS_DIR, "train")
VAL_DIR = os.path.join(SPLITS_DIR, "val")
TEST_DIR = os.path.join(SPLITS_DIR, "test")
UNAUGMENTED_DIR = os.path.join(SPLITS_DIR, "train_unaugmented")

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")

NORM_FILE = os.path.join(MODEL_DIR, "norms.npz")

VIS_DIR = os.path.join(PROJECT_ROOT, "visuals")
ROC_PLOTS_DIR = os.path.join(VIS_DIR, "roc")
ANOM_TIME_SERIES_PLOTS_DIR = os.path.join(VIS_DIR, "anom_time_series")

CHECKPOINT_NAME = "best_model"

PRED_DIR = os.path.join(PROJECT_ROOT, "predictions")
DEMO_PRED_FILE = os.path.join(PRED_DIR, "demo_predictions.npz")
ANOMALY_PRED_FILE = os.path.join(PRED_DIR, "anomaly_predictions.npz")
BASELINE_PRED_FILE = os.path.join(PRED_DIR, "baseline_predictions.npz")


PS_ONLY_SIM_DIR = os.path.join(PROJECT_ROOT, "data", "ps_only_sim")
