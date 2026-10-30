"""Data models for detector input payloads."""

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from tsmadkit.types import NonEmptyStr


class DataDict(BaseModel):
    """
    Time-aligned signal data.

    ``time`` contains the sample timestamps. ``values`` maps each signal name
    to its sample values, where each signal value list must have the same
    length as ``time``.

    Example::

        {
            "time": [0.0, 0.1, 0.2],
            "values": {
                "signal_1": [0.1, 0.2, 0.3],
                "signal_2": [0.4, 0.5, 0.6],
            },
        }

    """
    model_config = ConfigDict(extra="forbid")

    time: list[float]
    values: dict[NonEmptyStr, list[Any]]

    @model_validator(mode="after")
    def validate_sample_lengths(self):
        num_samples = len(self.time)
        for signal_name, signal_values in self.values.items():
            if len(signal_values) != num_samples:
                raise ValueError(
                    f"values.{signal_name}: 'time' and signal values must have "
                    "the same length"
                )
        return self
