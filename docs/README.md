# Documentation

This directory contains the Sphinx documentation for the whole repository, covering both Python packages:

- `tsmadkit`: core anomaly detection framework and base classes
- `tsmadalg`: algorithm catalog, registry, CLI, and concrete implementations built on top of `tsmadkit`

The documentation source lives in the `source/` folder.
The same source produces both the interactive HTML manual (`build/html/`) and the PDF manual (`build/latex/`).
Everything under `build/` is generated and not tracked by Git.

## Requirements

Install the documentation dependencies:

```bash
pip install -r requirements.txt
```

For local development, also install both packages in editable mode so Sphinx can import them correctly:

```bash
pip install -e ../src/tsmadkit
pip install -e ../src/tsmadalg
```

## Building the documentation

From the `docs/` directory:

1. Clean the previous build output:

```bash
make clean
```

2. Build the HTML documentation:

```bash
make html
```

The generated site will be available under `build/html/`.

3. Build the PDF documentation (requires a LaTeX distribution with `latexmk` and `pdflatex`):

```bash
make latexpdf
```

The generated PDF will be available under `build/latex/`.

## Documentation structure

- `source/index.rst`: main landing page for the full documentation site
- `source/getting-started.rst`: installation and package overview
- `source/architecture.rst`: relationship between `tsmadkit` and `tsmadalg`
- `source/api/`: API reference pages for both packages
- `source/algorithms/`: algorithm catalog entry point
- `source/guides/`: contributor-oriented guides such as creating a new algorithm
- `source/conf.py`: Sphinx configuration and build-time generation logic

## Algorithm catalog generation

Algorithm documentation pages are generated automatically at Sphinx build time by `generate_algorithm_docs()` in `source/conf.py`.

During `make html`, Sphinx scans:

```text
../src/tsmadalg/tsmadalg/algorithms/
```

For each algorithm subpackage containing a `main.py` file, it generates a page under:

```text
source/algorithms/generated/
```

These pages are rebuilt on every build and are not tracked by Git.

Each generated algorithm page may include:

- the algorithm README rendered from `README.md`
- the example JSON configuration rendered from `example_config.json`
- the autodocumented implementation from `main.py`

This means you do not need to run `sphinx-apidoc` manually for algorithms, and adding a new algorithm package automatically adds a new documentation page on the next build.
