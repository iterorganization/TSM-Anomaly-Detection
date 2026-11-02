# Anomaly Detection Algorithms

[![Build](https://img.shields.io/github/actions/workflow/status/iterorganization/TSM-Anomaly-Detection/python-tests.yml?branch=main&label=Build)](https://github.com/iterorganization/TSM-Anomaly-Detection/actions/workflows/python-tests.yml)
[![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.15-blue?logo=python&logoColor=white)](.github/workflows/python-tests.yml)
[![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL--3.0-ea7233)](COPYING.LESSER)

This repository is used for the development of time-resolved and intershot anomaly detection algorithms for the TSM framework.
The repository contains two main Python packages:

- **`tsmadkit`** (*TSM Anomaly Detection Kit*): a lightweight framework for implementing anomaly detection algorithms with a consistent interface. See `src/tsmadkit/README.md` for details.
- **`tsmadalg`** (*TSM Anomaly Detection Algorithms*): a catalog of anomaly detection algorithms implemented using `tsmadkit`, with a CLI for discovering, scaffolding, and running them. See `src/tsmadalg/README.md` for details.

These algorithms are designed to interface with the main TSM C++ code as standard monitoring applications.

## Repository Structure

Below is a high-level structure of the repository:

```
├── src/
│   ├── tsmadkit/      <- Core framework package
│   └── tsmadalg/      <- Catalog of implemented algorithms
├── docs/              <- Sphinx documentation (HTML and PDF manuals) for tsmadkit/tsmadalg
├── utils/             <- Code for offline postprocessing or building models/configurations
├── tests/
│   ├── unit/          <- Automated unit tests, run with pytest
│   └── integration/   <- Per-algorithm integration test scripts, run on synthetic data
└── examples/          <- Standalone usage examples
```

## Installation

### Setting up the environment

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Installing the packages

Navigate to each package directory and install in editable mode.
**Note:** Install `tsmadkit` first, as `tsmadalg` depends on it.

**Install `tsmadkit`:**

```bash
cd src/tsmadkit/
pip install -e .
```

**Install `tsmadalg`:**

```bash
cd ../tsmadalg/
pip install -e .
```

**Note:** Static analyzers such as Pylance cannot follow the default editable installs.
To let them resolve the packages, install them with `pip install -e . --config-settings editable_mode=compat` instead.

Each package also declares optional dependency extras (e.g. for development, ML model support, or the `tsmadalg` CLI).
See the package READMEs linked above for the full list.

## Documentation

Full API documentation for `tsmadkit` and `tsmadalg` is available in the `docs/` folder.
The documentation is built using Sphinx, as an interactive HTML manual and a PDF manual.

### Building the documentation

Navigate to the `docs/` directory and install the requirements:

```bash
cd docs/
pip install -r requirements.txt
```

Build the HTML documentation:

```bash
make clean
make html
```

Open `build/html/index.html` in a browser to view the documentation.

Build the PDF documentation (requires a LaTeX distribution with `latexmk` and `pdflatex`):

```bash
make latexpdf
```

The PDF is written to `build/latex/`.
See `docs/README.md` for more details.

## Testing

Before running tests, ensure both packages are installed in editable mode with the `dev` extra:

```bash
pip install -e src/tsmadkit[dev]
pip install -e src/tsmadalg[dev]
```

or that `pytest` (and optionally `pytest-cov`) is installed separately.

### Unit tests

Unit tests for both `tsmadkit` and `tsmadalg` are provided in the `tests/unit/` folder.
Run all of them from the repository root:

```bash
pytest tests
```

Run specific test suites:

```bash
# Run only tsmadkit tests
pytest tests/unit/tsmadkit/

# Run only tsmadalg tests
pytest tests/unit/tsmadalg/

# Run with coverage report
pytest tests/unit/tsmadkit/ --cov=tsmadkit
pytest tests/unit/tsmadalg/ --cov=tsmadalg
```

### Integration tests

The `tests/integration/` folder contains one folder per algorithm, with a script that runs the algorithm on synthetic data and reports its true-positive and false-positive rates.
These scripts are not collected by `pytest`, and may need the algorithm's own dependencies.
See the README in each folder for requirements and instructions.

## Citation

If you use `tsmadkit` or `tsmadalg` in a scientific publication, please consider citing the following article:

> Paret et al. (2026). [Design and implementation of machine learning-based anomaly detection in the ITER Tokamak Systems Monitor](https://doi.org/10.3389/fphy.2026.1824578). *Frontiers in Physics* 14:1824578.

BibTeX entry:

```bibtex
@article{Paret2026TSM,
  author  = {Paret, Joris and Sammuli, Brian and Costa Pérez, Víctor and Saura, Nathaniel and Hernández Cubo, Laura and Iglesias, Daniel},
  title   = {Design and implementation of machine learning-based anomaly detection in the {ITER} {Tokamak Systems Monitor}},
  journal = {Frontiers in Physics},
  volume  = {14},
  pages   = {1824578},
  year    = {2026},
  doi     = {10.3389/fphy.2026.1824578},
  issn    = {2296-424X}
}
```

## License

The `tsmadkit` and `tsmadalg` packages are released under the [LGPL-3.0 License](COPYING.LESSER).
