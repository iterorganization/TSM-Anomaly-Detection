import pytest
from pydantic import ValidationError

from tsmadkit.data import DataDict


def test_data_dict_accepts_matching_time_and_signal_lengths(data_dict):
    """
    Test that DataDict accepts a valid input where the length of the time list
    matches the length of each signal's values list.
    """
    data = DataDict.model_validate(data_dict)

    assert data.time == data_dict["time"]
    assert data.values == data_dict["values"]


def test_data_dict_rejects_signal_values_with_wrong_length(data_dict):
    """
    Test that DataDict raises a ValidationError when the length of a signal's
    values list does not match the length of the time list.
    """
    data_dict["values"]["sensor_1"] = [0.2, 0.4]

    with pytest.raises(ValidationError, match="values.sensor_1"):
        DataDict.model_validate(data_dict)
