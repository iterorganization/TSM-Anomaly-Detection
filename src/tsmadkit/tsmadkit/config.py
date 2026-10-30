"""
Configuration schema definitions for anomaly detection algorithms.

This module defines Pydantic models that represent the expected structure of the configuration
files used to initialize anomaly detection algorithms.
"""

import hashlib
import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tsmadkit.types import NonEmptyStr

class SignalsConfig(BaseModel):
    """Configuration schema for signals specification in anomaly detection algorithms.
    
    This class defines the expected structure of the "signals" section in the algorithm 
    configuration file. It includes fields for target signals and optional context 
    signals, with validation to ensure uniqueness.
    """
    model_config = ConfigDict(extra="forbid")

    targets: list[NonEmptyStr]
    context: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def verify_unique_names(self):
        if len(set(self.targets)) != len(self.targets):
            raise ValueError("targets must be unique")
        if len(set(self.context)) != len(self.context):
            raise ValueError("context must be unique")
        return self


class ModelConfig(BaseModel):
    """
    Configuration schema for model loading in anomaly detection algorithms.

    This class defines the expected structure of the "model" configuration section in
    the algorithm configuration file. It includes fields for the source of the model
    and the path to the model file
    """
    model_config = ConfigDict(extra="forbid")

    source: Literal["scikit-learn", "keras", "tensorflow", "custom"] | None
    path: NonEmptyStr


class ReferenceStateConfig(BaseModel):
    """
    Configuration for optional reference state tracking in anomaly detection algorithms.

    This class defines the expected structure of the "reference_state" section in
    the algorithm configuration file. It includes fields for the path to the
    reference state file and optional state checking policy.
    """
    model_config = ConfigDict(extra="forbid")

    path: NonEmptyStr
    check: Literal["fast", "full"] = "fast"


class AlgorithmConfig(BaseModel):
    """
    Configuration schema for anomaly detection algorithms.
    
    This class defines the expected structure of the configuration file that anomaly
    detection algorithms should adhere to. It includes fields for algorithm name,
    parameters, model configuration, signals specification, artifacts, anomaly
    classes, and reference state configuration.
    """
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    parameters: dict[str, Any] | None = None
    model: ModelConfig | None = None
    signals: SignalsConfig
    artifacts: list[NonEmptyStr] | None = None
    anomaly_classes: list[NonEmptyStr] | None = None
    reference_state: ReferenceStateConfig | None = None

    @model_validator(mode="after")
    def verify_unique_values(self):
        if self.artifacts is not None and len(set(self.artifacts)) != len(self.artifacts):
            raise ValueError("artifacts must be unique")
        if self.anomaly_classes is not None and len(set(self.anomaly_classes)) != len(self.anomaly_classes):
            raise ValueError("anomaly_classes must be unique")
        return self

    def sha256(self) -> str:
        """
        Compute the SHA-256 hash of the configuration content.

        The hash is computed from a canonical JSON serialization of the
        validated configuration, so it does not depend on whether the
        configuration was read from a file or passed as a dictionary, nor on
        key order or formatting. The ``reference_state`` section is excluded
        because it describes how to check the reference state, not what the
        algorithm computes.

        Returns
        -------
        str
            Hexadecimal SHA-256 digest of the configuration.

        Raises
        ------
        pydantic_core.PydanticSerializationError
            If the configuration contains values that are not JSON serializable.
        """
        content = self.model_dump(mode="json", exclude={"reference_state"})
        text = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()
