from tsmadkit import AnomalyDetection, AnomalyResult
from tsmadkit.signals import SignalSet

import torch
from mag_ps_cinn.model import PsCINN

class MAGPowerSupply(AnomalyDetection):
    """Magnet power-supply anomaly detection with a conditional invertible neural network (cINN)."""

    __version__ = "0.0.1"

    def setup(self) -> None:
        """
        Load the model from a checkpoint (.ckpt), set it in eval mode
        on the configured device, and define some useful loop-independent
        constants to be used in the `detect` method.
        """
        # Model loading
        model_path = self.model_config["path"]
        self.model = PsCINN.load_from_checkpoint(model_path)
        self.model.eval()
        self.model.to(self.device)
        # Loop independent constants
        self.commands_idx = slice(0, 12)
        self.simulated_voltages_idx = slice(12, 24)
        self.target_signals_idx = torch.tensor(range(12))
        # NLL thresholds (from the JSON config)
        self.nll_thresholds = torch.as_tensor(self.nll_thresholds)

    def detect(self, data: SignalSet) -> AnomalyResult:
        """
        Detect anomalous magnet power-supply voltage windows via a
        conditional invertible neural network (CINN).

        Parameters
        ----------
        data : SignalSet
            Synchronized window of actuator commands, simulated voltages, and
            measured voltages sharing one time grid.

        Returns
        -------
        AnomalyResult
            Detection result with ``is_anomaly`` set when at least one target
            signal's NLL exceeds its configured threshold,
            ``scores["max_nll"]`` containing the largest NLL across target
            signals, and ``sources`` listing the target signals whose
            threshold was exceeded (``None`` when none were).
        """
        # Format the input data to use with the CINN
        commands = torch.as_tensor(data.context_values[self.commands_idx])
        simulated_voltages = torch.as_tensor(data.context_values[self.simulated_voltages_idx])
        measured_voltages = torch.as_tensor(data.target_values)
        # CINN inference
        with torch.no_grad():
            nll = self.model.forward(commands, simulated_voltages, measured_voltages, self.target_signals_idx)
        # Evaluate NLL thresholds for each signal
        anomalous = nll > self.nll_thresholds
        sources = None
        if is_anomalous := any(anomalous):
            sources = list(data.target_names[anomalous])
        # Format the output
        return AnomalyResult(is_anomaly=is_anomalous,
                             scores={"max_nll": float(max(nll))},
                             sources=sources)