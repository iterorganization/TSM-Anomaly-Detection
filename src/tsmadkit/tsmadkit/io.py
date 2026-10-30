"""
I/O utilities.
"""

import json
from pathlib import Path
from typing import Any

import h5py
from pydantic import ValidationError

from tsmadkit.data import DataDict
from tsmadkit.signals import SignalSet

DEFAULT_IO_ENCODING = "utf-8"
DEFAULT_JSON_INDENT = 4


def read_json(path: str | Path) -> Any:
    """
    Read and parse a JSON file.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the JSON file.

    Returns
    -------
    Any
        Parsed JSON value.

    Raises
    ------
    ValueError
        If the file does not contain valid JSON.
    """
    input_path = Path(path)
    try:
        with input_path.open("r", encoding=DEFAULT_IO_ENCODING) as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in '{input_path}': {exc.msg}") from exc


def write_json(obj: Any, path: str | Path) -> None:
    """
    Serialize a JSON-serializable object to a JSON file.

    Parameters
    ----------
    obj : Any
        JSON-serializable object to write.
    path : str or pathlib.Path
        Output path of the JSON file.
    """
    output_path = Path(path)
    with output_path.open("w", encoding=DEFAULT_IO_ENCODING) as f:
        json.dump(obj, f, indent=DEFAULT_JSON_INDENT)
        f.write("\n")


def read_json_input_data(path: str | Path) -> dict:
    """
    Load a JSON input-data payload from disk.

    Parameters
    ----------
    path : str or Path
        Path to the JSON file.

    Returns
    -------
    dict[str, Any]
        Input data dictionary.

    Raises
    ------
    ValueError
        If the JSON is invalid or the payload does not conform to the
        expected input-data format.
    """
    input_data = read_json(path)
    try:
        validated = DataDict.model_validate(input_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid input data: {exc}") from None

    return validated.model_dump()


def write_json_input_data(
    path: str | Path,
    data: SignalSet | DataDict | dict
) -> None:
    """
    Write an input-data payload to a JSON file.

    Note
    ----
    If `data` is an instance of `SignalSet`, the specification of
    signal roles (i.e. "targets"/"context") will be ignored.

    Parameters
    ----------
    path : str or Path
        Output path of the JSON file.
    data : SignalSet, DataDict or dict
        Input data in the framework format.
    """
    # Convert to dict
    if isinstance(data, SignalSet):
        data = data.to_dict()

    # Validate structure
    try:
        validated = DataDict.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid input data: {exc}") from None

    write_json(validated.model_dump(), path)


def read_hdf5_input_data(path: str | Path) -> dict:
    """
    Load an HDF5 input-data payload from disk.

    The HDF5 file mirrors the :class:`DataDict` structure with a top-level
    ``time`` dataset and a ``values`` group containing one dataset per signal.

    Parameters
    ----------
    path : str or Path
        Path to the HDF5 file.

    Returns
    -------
    dict[str, Any]
        Input data dictionary.

    Raises
    ------
    ValueError
        If the HDF5 payload does not conform to the expected input-data format.
    """
    input_path = Path(path)
    with h5py.File(input_path, "r") as f:
        try:
            values_group = f["values"]
            signal_names = json.loads(values_group.attrs["signal_names"])
            input_data = {
                "time": f["time"][()].tolist(),
                "values": {
                    name: values_group[name][()].tolist()
                    for name in signal_names
                },
            }
        except KeyError as exc:
            raise ValueError(f"Invalid HDF5 input data: missing {exc}") from None

    try:
        validated = DataDict.model_validate(input_data)
    except ValidationError as exc:
        raise ValueError(f"Invalid input data: {exc}") from None

    return validated.model_dump()


def write_hdf5_input_data(
    path: str | Path,
    data: SignalSet | DataDict | dict
) -> None:
    """
    Write an input-data payload to an HDF5 file.

    Note
    ----
    If `data` is an instance of `SignalSet`, the specification of
    signal roles (i.e. "targets"/"context") will be ignored.

    Parameters
    ----------
    path : str or Path
        Output path of the HDF5 file.
    data : SignalSet, DataDict or dict
        Input data in the framework format.
    """
    if isinstance(data, SignalSet):
        data = data.to_dict()

    try:
        validated = DataDict.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid input data: {exc}") from None

    input_data = validated.model_dump()
    signal_names = list(input_data["values"])

    output_path = Path(path)
    with h5py.File(output_path, "w") as f:
        f.create_dataset("time", data=input_data["time"])
        values_group = f.create_group("values")
        values_group.attrs["signal_names"] = json.dumps(signal_names)
        for name in signal_names:
            values_group.create_dataset(
                name,
                data=input_data["values"][name],
            )
