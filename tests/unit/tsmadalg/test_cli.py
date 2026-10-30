import argparse
import json

import pytest

from tsmadalg.tools import cli


def test_parse_json_object_accepts_only_json_objects():
    """Check that CLI JSON parsing accepts dictionaries and rejects other inputs."""
    assert cli._parse_json_object('{"threshold": 0.5}') == {"threshold": 0.5}

    with pytest.raises(argparse.ArgumentTypeError):
        cli._parse_json_object("[1, 2, 3]")

    with pytest.raises(argparse.ArgumentTypeError):
        cli._parse_json_object("{not json}")


def test_cli_list_prints_registry_entries(fake_algorithms, capsys):
    """Check that the list command prints available and unavailable registry entries."""
    cli.cmd_list(argparse.Namespace())

    output = capsys.readouterr().out
    assert "fake_algorithm" in output
    assert "1.2.3" in output
    assert "unavailable_algorithm" in output
    assert "missing optional dependency" in output


def test_cli_run_writes_detection_result(
    fake_algorithms,
    fake_algorithm_config,
    input_payload,
    tmp_path,
):
    """Check that the run command executes a fake detector and writes its JSON result."""
    output_path = tmp_path / "result.json"

    cli.cmd_run(
        argparse.Namespace(
            name="fake_algorithm",
            config=str(fake_algorithm_config),
            input=str(input_payload),
            output=output_path,
        )
    )

    assert json.loads(output_path.read_text()) == {
        "details": None,
        "is_anomaly": True,
        "label": "anomaly",
        "time_min": None,
        "time_max": None,
        "scores": {"anomaly": 0.75},
        "sources": ["signal_a"],
        "message": None,
    }
