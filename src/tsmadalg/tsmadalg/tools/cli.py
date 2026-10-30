import argparse
import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from tsmadalg.tools.registry import list_algorithms, get_algorithm_class
from tsmadalg.tools.templates import generate_algorithm_template
from tsmadkit.io import read_json_input_data
from tsmadkit.signals import SignalSet

console = Console()

def main():
    parser = argparse.ArgumentParser(
        prog="tsmadalg",
        description="CLI tools for TSM Anomaly Detection algorithms",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------------------
    # tsmadalg list
    # -------------------
    list_parser = subparsers.add_parser(
        "list", help="List all discovered anomaly detection algorithms and their status",
        description=(
            "List all anomaly detection algorithms discovered in the tsmadalg.algorithms package.\n\n"
            "For each algorithm, display its name, version, availability status, and details about its implementation or import errors."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    list_parser.set_defaults(func=cmd_list)

    # -------------------
    # tsmadalg create
    # -------------------
    create_parser = subparsers.add_parser(
        "create", help="Create a new algorithm template",
        description=(
            "Generate a new anomaly detection algorithm template with boilerplate code.\n\n"
            "This command creates a new algorithm directory containing:\n"
            "- A Python class template inheriting from AnomalyDetection\n"
            "- An example_config.json file following the required schema\n"
            "- An empty __init__.py file\n\n"
            "If the algorithm is placed within the tsmadalg.algorithms package, it will be automatically discovered by the package.\n"
            "If not, add the path to the new algorithm directory in the TSMADALG_EXT_PATH environment variable to have it included in the registry."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    create_parser.add_argument(
        "name",
        help="Algorithm name (e.g., 'my_detector' or 'MyDetector')"
    )
    create_parser.add_argument(
        "--version",
        default="0.0.1",
        help="Initial version (default: 0.0.1)"
    )
    create_parser.add_argument(
        "--target-signals",
        "--signals",
        dest="target_signals",
        nargs="+",
        help="Target signal names to include in the example config"
    )
    create_parser.add_argument(
        "--context-signals",
        nargs="+",
        help="Context signal names to include in the example config"
    )
    create_parser.add_argument(
        "--parameters",
        type=_parse_json_object,
        help="Initial parameters as a JSON object, e.g. '{\"threshold\": 0.5}'"
    )
    create_parser.add_argument(
        "--model-source",
        choices=["scikit-learn", "keras", "tensorflow", "custom"],
        help="Model source type"
    )
    create_parser.add_argument(
        "--model-path",
        help="Path to the model file"
    )
    create_parser.add_argument(
        "--anomaly-classes",
        nargs="+",
        help="Anomaly class names to include in the example config"
    )
    create_parser.add_argument(
        "--artifacts",
        nargs="+",
        help="Artifact file paths to include in the example config"
    )
    create_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where the algorithm folder will be created"
    )
    create_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if directory exists"
    )
    create_parser.set_defaults(func=cmd_create)

    # -------------------
    # tsmadalg run
    # -------------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run a specific algorithm on a provided dataset",
        description=(
            "Run an anomaly detection algorithm on an input JSON payload.\n\n"
            "This command:\n"
            "- Loads the selected algorithm from the registry\n"
            "- Instantiates it from a JSON configuration file\n"
            "- Validates and loads the input payload from disk\n"
            "- Runs the algorithm on the provided data\n"
            "- Writes the resulting anomaly detection output to JSON\n\n"
            "Input JSON format:\n"
            "- Required: 'time' = list of sample timestamps\n"
            "- Required: 'values' = object mapping signal names to lists of values,\n"
            "  each the same length as 'time'"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "name",
        help="Algorithm name"
    )
    run_parser.add_argument(
        "--config",
        required=True,
        help="Path to JSON config file"
    )
    run_parser.add_argument(
        "--input",
        required=True,
        help="Path to input data file"
    )
    run_parser.add_argument(
        "--output",
        required=False,
        default=None,
        help="Optional path to write the JSON result. Defaults to \"<algo_name>_result.json\""
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)

def cmd_list(args):
    """Handle the list command."""
    algs = list_algorithms()

    # Create a rich table
    table = Table(
        title="[bold cyan]Discovered Anomaly Detection Algorithms[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Details", style="white")

    # Add each algorithm entry
    for name, alg in algs.items():
        if alg["class"] is not None:
            details = f"{alg['module']}:{alg['class'].__name__}"
        elif alg["status"] == "unavailable":
            details = alg["error_message"] or "-"
        else:
            details = f"{alg['module']} (not resolved)"

        table.add_row(
            name,
            alg["version"] or "-",
            alg["status"],
            details,
        )

    console.print(table)

def cmd_create(args):
    """Handle the create command."""
    output_path = generate_algorithm_template(
        algorithm_name=args.name,
        version=args.version,
        parameters=args.parameters,
        model_source=args.model_source,
        model_path=args.model_path,
        anomaly_classes=args.anomaly_classes,
        artifacts=args.artifacts,
        target_signals=args.target_signals,
        context_signals=args.context_signals,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    console.print(f"\n[bold green]✓[/bold green] Successfully created algorithm template at: [cyan]{output_path}[/cyan]")
    console.print(f"\n[bold yellow]Next steps:[/bold yellow]")
    console.print(f"  [bold]1.[/bold] Edit [cyan]{output_path / 'main.py'}[/cyan] to implement your detection logic")
    console.print(f"  [bold]2.[/bold] Update [cyan]{output_path / 'example_config.json'}[/cyan] with your parameters")
    console.print(f"  [bold]3.[/bold] Test your algorithm: [green]tsmadalg list[/green]")

def cmd_run(args):
    """Handle the run command."""

    # Collect input/output paths
    config = Path(args.config)
    input_json = Path(args.input)

    if args.output is None:
        output_json = f"{args.name}_result.json"
    else:
        output_json = Path(args.output)

    console.print("[bold blue]tsmadalg run[/bold blue]")
    console.print(f"  algorithm: [cyan]{args.name}[/cyan]")
    console.print(f"  config:    [cyan]{config}[/cyan]")
    console.print(f"  input:     [cyan]{input_json}[/cyan]")
    console.print(f"  output:    [cyan]{output_json}[/cyan]")

    # Validate input paths early
    console.print("[yellow]Checking input files...[/yellow]")
    if not config.exists():
        raise FileNotFoundError(f"Configuration file not found: '{config}'")
    if not input_json.exists():
        raise FileNotFoundError(f"Input data file not found: '{input_json}'")

    output_parent = output_json.parent
    if output_parent and not output_parent.exists():
        raise FileNotFoundError(
            f"Output directory does not exist: '{output_parent}'"
        )
    if output_parent and not output_parent.is_dir():
        raise ValueError(
            f"Output parent path is not a directory: '{output_parent}'"
        )
    console.print("[green]Input files look OK.[/green]")

    # Resolve the algorithm class
    console.print("[yellow]Resolving algorithm class...[/yellow]")
    cls = get_algorithm_class(args.name)
    console.print(
        f"[green]Resolved[/green] [cyan]{args.name}[/cyan] "
        f"[dim]({cls.__module__}.{cls.__name__})[/dim]"
    )

    # Instantiate detector
    console.print("[yellow]Instantiating detector from config...[/yellow]")
    detector = cls(str(config))
    console.print("[green]Detector instantiated.[/green]")

    # Load payload
    console.print("[yellow]Loading input payload...[/yellow]")
    data_dict = read_json_input_data(input_json)
    console.print("[green]Payload loaded.[/green]")

    # Detector setup
    console.print("[yellow]Preparing detector...[/yellow]")
    detector.setup()
    console.print("[green]Detector setup complete.[/green]")

    # Run inference
    console.print("[yellow]Running detection...[/yellow]")
    signal_set = SignalSet.from_dict(data_dict, signal_spec=detector.signal_spec)
    result = detector.detect(signal_set)
    console.print("[green]Detection complete.[/green]")

    # Serialize
    console.print("[yellow]Writing result...[/yellow]")
    result.to_json(output_json)
    console.print(f"[bold green]Result written to[/bold green] [cyan]{output_json}[/cyan]")


def _parse_json_object(value: str) -> dict[str, Any]:
    """Parse a JSON object passed as a CLI argument."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON object: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("Expected a JSON object, e.g. '{\"threshold\": 0.5}'")

    return parsed


if __name__ == "__main__":
    main()
