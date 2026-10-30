import pytest

from tsmadkit.io import (
    DEFAULT_IO_ENCODING,
    read_json,
    write_json,
    read_json_input_data,
    write_json_input_data,
    read_hdf5_input_data,
    write_hdf5_input_data
)


def test_read_json_reads_valid_json(tmp_path):
    """
    Test that read_json correctly reads a valid JSON file and returns the
    expected dictionary.
    """
    input_path = tmp_path / "payload.json"
    input_path.write_text('{"a": 1, "b": [2, 3]}\n', encoding=DEFAULT_IO_ENCODING)

    assert read_json(input_path) == {"a": 1, "b": [2, 3]}


def test_read_json_rejects_invalid_json(tmp_path):
    """
    Test that read_json raises a ValueError when the JSON file contains
    invalid JSON.
    """
    input_path = tmp_path / "payload.json"
    input_path.write_text('{"a": 1,,}\n', encoding=DEFAULT_IO_ENCODING)

    with pytest.raises(ValueError, match="Invalid JSON in"):
        read_json(input_path)

def test_read_json_input_data_reads_data_dict(tmp_path, data_dict):
    """
    Test that read_json_input_data correctly reads a valid input JSON file.
    """
    # Write data dict to file
    input_path = tmp_path / "input.json"
    write_json(data_dict, input_path)

    # Read it back
    input_data = read_json_input_data(input_path)

    assert input_data == data_dict

def test_write_json_input_data_writes_data_dict(tmp_path, data_dict):
    """
    Test that write_json_input_data correctly writes an input DataDict data
    to a JSON file, and that read_json_input_data can read it back correctly.
    """
    output_path = tmp_path / "input.json"
    write_json_input_data(output_path, data_dict)

    input_data = read_json_input_data(output_path)
    assert input_data == data_dict

def test_write_json_input_data_writes_signal_set(tmp_path, signal_set):
    """
    Test that write_json_input_data correctly writes an input SignalSet data
    to a JSON file, and that read_json_input_data can read it back correctly.
    """
    output_path = tmp_path / "input.json"
    write_json_input_data(output_path, signal_set)

    input_data = read_json_input_data(output_path)
    assert input_data == signal_set.to_dict()


def test_write_hdf5_input_data_writes_data_dict(tmp_path, data_dict):
    """
    Test that write_hdf5_input_data correctly writes input DataDict data
    to an HDF5 file, and that read_hdf5_input_data can read it back correctly.
    """
    output_path = tmp_path / "input.h5"
    write_hdf5_input_data(output_path, data_dict)

    input_data = read_hdf5_input_data(output_path)
    assert input_data == data_dict


def test_write_hdf5_input_data_writes_signal_set(tmp_path, signal_set):
    """
    Test that write_hdf5_input_data correctly writes input SignalSet data
    to an HDF5 file, and that read_hdf5_input_data can read it back correctly.
    """
    output_path = tmp_path / "input.h5"
    write_hdf5_input_data(output_path, signal_set)

    input_data = read_hdf5_input_data(output_path)
    assert input_data == signal_set.to_dict()
