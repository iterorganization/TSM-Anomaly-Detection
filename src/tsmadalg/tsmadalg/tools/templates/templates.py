"""
Template generator for creating new anomaly detection algorithm templates.
"""

import json
import re
from pathlib import Path
from typing import Any, Literal
from importlib import resources
from string import Template

from rich.console import Console
from tsmadkit.config import AlgorithmConfig, ModelConfig, SignalsConfig

from tsmadalg import algorithms

console = Console()

def generate_algorithm_template(
    algorithm_name: str,
    version: str = "0.0.1",
    parameters: dict[str, Any] | None = None,
    model_source: Literal["scikit-learn", "keras", "tensorflow", "custom"] | None = None,
    model_path: str | None = None,
    anomaly_classes: list[str] | None = None,
    artifacts: list[str] | None = None,
    target_signals: list[str] | None = None,
    context_signals: list[str] | None = None,
    output_dir: Path | str | None = None,
    overwrite: bool = False,
) -> Path:
    """
    Create a template for a new anomaly detection algorithm.

    This function generates a new algorithm directory with:
    - A Python class template inheriting from AnomalyDetection
    - An example_config.json file following the required schema
    - An __init__.py file re-exporting the class

    Parameters
    ----------
    algorithm_name : str
        Name of the algorithm (e.g., "my_anomaly_detector" or "MyAnomalyDetector").
        Will be converted to appropriate directory and class names.
    version : str, default="0.0.1"
        Initial version string for the algorithm.
    parameters : dict, optional
        Initial parameters dictionary for the example config. If None, an empty dict
        will be used.
    model_source : str, optional
        Model source type ("scikit-learn", "keras", "tensorflow", "custom", or None).
        If provided, model_path must also be provided.
    model_path : str, optional
        Path to the model file. Required if model_source is provided.
    anomaly_classes : list[str], optional
        List of anomaly class names. If None, defaults to ["anomaly"].
    artifacts : list[str], optional
        List of artifact file paths (additional files needed by the algorithm).
    target_signals : list[str], optional
        List of signal names to include in the example config. If None, a placeholder
        will be included.
    context_signals : list[str], optional
        List of context signal names to include in the example config. If None, no context signals will be included.
    output_dir : Path or str, optional
        Directory where the algorithm folder will be created. If None, defaults to
        the tsmadalg.algorithms package directory.
    overwrite : bool, default=False
        If True, overwrite existing files. If False, raise an error if the directory
        already exists.

    Returns
    -------
    Path
        Path to the created algorithm directory.

    Raises
    ------
    ValueError
        If algorithm_name is invalid, if model_source is provided without model_path,
        or if the directory already exists and overwrite=False.
    FileExistsError
        If the algorithm directory already exists and overwrite=False.
    """
    # Validate algorithm name
    _validate_algorithm_name(algorithm_name)

    # Convert to directory name (snake_case)
    dir_name = _to_snake_case(algorithm_name)

    # Convert to class name (PascalCase)
    class_name = _to_pascal_case(algorithm_name)

    # Determine output directory
    if output_dir is None:
        algorithms_dir = Path(algorithms.__file__).parent
    else:
        algorithms_dir = Path(output_dir)

    algorithm_dir = algorithms_dir / dir_name

    # Check if directory already exists
    if algorithm_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Algorithm directory '{algorithm_dir}' already exists. "
            "Set overwrite=True to overwrite existing files."
        )

    # Create directory structure
    algorithm_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py, re-exporting the class
    init_file = algorithm_dir / "__init__.py"
    init_file.write_text(f"from .main import {class_name}\n")

    # Create main.py with template class
    main_template = _generate_main_template(
        class_name=class_name,
        version=version,
    )
    main_file = algorithm_dir / "main.py"
    main_file.write_text(main_template)

    # Create example_config.json with template config
    config_dict = _generate_config_dict(
        algorithm_name=algorithm_name,
        target_signals=target_signals or ["SIGNAL_1", "SIGNAL_2"],
        context_signals=context_signals,
        parameters=parameters or {},
        model_source=model_source,
        model_path=model_path,
        anomaly_classes=anomaly_classes,
        artifacts=artifacts,
    )
    config_file = algorithm_dir / "example_config.json"
    config_file.write_text(json.dumps(config_dict, indent=4) + "\n")

    console.print(f"[bold green]✓[/bold green] Created algorithm template: [cyan]{algorithm_dir}[/cyan]")
    console.print(f"  [bold]•[/bold] Class: [yellow]{class_name}[/yellow]")
    console.print(f"  [bold]•[/bold] Config: [blue]{config_file.name}[/blue]")

    return algorithm_dir


def _to_pascal_case(name: str) -> str:
    """Convert algorithm name to PascalCase class name."""
    # Handle snake_case, kebab-case, and space-separated names
    parts = re.split(r'[-_\s]+', name)
    return ''.join(word[:1].upper() + word[1:] for word in parts if word)


def _to_snake_case(name: str) -> str:
    """Convert algorithm name to snake_case directory name."""
    # Insert underscores before uppercase letters (except first)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def _validate_algorithm_name(name: str) -> None:
    """Validate that algorithm name is suitable for directory and Python identifier."""
    if not name:
        raise ValueError("Algorithm name cannot be empty")
    
    # Check if it's a valid Python identifier
    if not name.replace('_', '').replace('-', '').isalnum():
        raise ValueError(
            f"Algorithm name '{name}' contains invalid characters. "
            "Use only alphanumeric characters, underscores, or hyphens."
        )
    
    # Check if it starts with a number
    if name[0].isdigit():
        raise ValueError("Algorithm name cannot start with a digit")


def _generate_main_template(
    class_name: str,
    version: str,
) -> str:
    """Generate the content for main.py"""
    # Template file
    filename = "base.txt"

    # Load the template and substitute values
    templates_package = "tsmadalg.tools.templates"
    template = resources.files(templates_package).joinpath(filename).read_text()
    values = {"class_name": class_name, "version": version}
    rendered = Template(template).substitute(values)

    compile(rendered, "<generated main.py>", "exec")
    return rendered


def _generate_config_dict(
    algorithm_name: str,
    parameters: dict[str, Any] | None,
    model_source: Literal["scikit-learn", "keras", "tensorflow", "custom"] | None,
    model_path: str | None,
    anomaly_classes: list[str] | None,
    artifacts: list[str] | None,
    target_signals: list[str],
    context_signals: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a config dictionary for the example_config.json file."""
    if (model_source is None) != (model_path is None):
        raise ValueError(
            "Both model_source and model_path must be provided together, or both None"
        )

    model = None
    if model_source is not None and model_path is not None:
        model = ModelConfig(source=model_source, path=model_path)

    config = AlgorithmConfig(
        name=algorithm_name,
        parameters=parameters or {},
        model=model,
        anomaly_classes=anomaly_classes,
        artifacts=artifacts,
        signals=SignalsConfig(
            targets=target_signals,
            context=context_signals or [],
        ),
    )

    return config.model_dump(mode="json", exclude_none=True)
