import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from tsmadkit.io import read_json, write_json
from tsmadkit.types import NonEmptyStr

if TYPE_CHECKING:
    import pandas as pd


class AnomalyResult(BaseModel):
    """
    Standardized output structure for anomaly detection results.

    Parameters
    ----------
    is_anomaly : bool
        Primary decision flag indicating whether the input is anomalous.
    scores : dict[str, float]
        Unified scoring output. For binary detectors, use {"anomaly": s} for a single
        anomaly score `s`. For multiclass, provide per-class scores or probabilities,
        e.g. {"OK": 0.92, "arc": 0.06, "misfire": 0.02}. Semantics (probability,
        margin, distance) are algorithm-defined and should be documented by the
        implementing class.
    label : str, optional
        Predicted class name when the algorithm performs classification (e.g. "arc",
        "misfire", "OK"). Binary detectors may set this to "anomaly" when `is_anomaly`
        is True or omit it entirely.
    time_min : int | float, optional
        Minimum time value in the detected anomaly window.
    time_max : int | float, optional
        Maximum time value in the detected anomaly window.
    sources : list[str], optional
        Signals or features that contributed most to the decision.
    details: dict[str, Any], optional
        Algorithm-specific values that provide additional context for analysis or
        visualization of the result.
    message : str, optional
        Short human-readable explanation of the decision.

    Notes
    -----
    Downstream systems must rely on `is_anomaly` for warnings and `scores` for an
    initial severity estimate. Other fields provide context only when available.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    is_anomaly: bool
    scores: dict[NonEmptyStr, float]
    label: NonEmptyStr | None = None
    time_min: int | float | None = None
    time_max: int | float | None = None
    sources: list[NonEmptyStr] | None = None
    details: dict[NonEmptyStr, Any] | None = None
    message: NonEmptyStr | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the `AnomalyResult` object into a dictionary for easy serialization and storage.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the `AnomalyResult` object, where keys are attribute names and values are their corresponding values.
        """
        return self.model_dump()

    def to_json(self, path: str | Path) -> None:
        """
        Serialize the result to a JSON file.

        Parameters
        ----------
        path : str or pathlib.Path
            Output path of the JSON file.
        """
        write_json(self.to_dict(), path=path)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnomalyResult":
        """
        Build an `AnomalyResult` from a dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary representation of an anomaly result.

        Returns
        -------
        AnomalyResult
            Validated anomaly result.

        Raises
        ------
        ValidationError
            If the input data does not conform to the expected structure or types.
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, path: str | Path) -> "AnomalyResult":
        """
        Load an `AnomalyResult` from a JSON file.

        Parameters
        ----------
        path : str or pathlib.Path
            Path to the JSON file.

        Returns
        -------
        AnomalyResult
            Validated anomaly result loaded from the file.

        Raises
        ------
        ValidationError
            If the JSON content does not conform to the expected structure or types. 
        """
        data = read_json(path=path)
        return cls.from_dict(data)

    @staticmethod
    def to_dataframe(results: list["AnomalyResult"]) -> "pd.DataFrame":
        """
        Convert a list of `AnomalyResult` objects into a pandas DataFrame.

        Parameters
        ----------
        results : list of AnomalyResult
            List of `AnomalyResult` objects.

        Returns
        -------
        pandas.DataFrame
            A DataFrame where each row corresponds to an `AnomalyResult`,
            with columns named after the dataclass fields.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "pandas is required for AnomalyResult.to_dataframe(). "
                "Install it separately with `pip install pandas`."
            ) from exc

        return pd.DataFrame([result.to_dict() for result in results])
