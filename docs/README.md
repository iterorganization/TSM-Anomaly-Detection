# Documentation

This directory contains the Sphinx documentation for the whole repository, covering both Python packages:

- `tsmadkit`: core anomaly detection framework and base classes
- `tsmadalg`: algorithm catalog, registry, CLI, and concrete implementations built on top of `tsmadkit`

The documentation source lives in the `source/` folder.
The same source produces both the interactive HTML manual (`build/html/`) and the PDF manual (`build/latex/`).
Everything under `build/` is generated and not tracked by Git.

## Online documentation

The HTML documentation is published on GitHub Pages at https://iterorganization.github.io/TSM-Anomaly-Detection/ by the `.github/workflows/docs.yml` workflow.
Each version is built separately and stored in its own folder of the `gh-pages` branch:

- a push to `main` updates `stable/`
- a push to `dev` updates `dev/`
- a release tag such as `v0.1.0` creates `0.1.0/`

The workflow also runs `write_versions.py`, which writes `versions.json` and redirects the site root to `stable/`.
`versions.json` lists `stable`, `dev`, and one version per `vX.Y.Z` tag, and is read by the version menu at the bottom of the sidebar (`source/_templates/versions.html`).
Locally built documentation is labeled `dev` in the version menu, unless the `DOCS_VERSION` environment variable is set.

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
- `source/citing.rst`: how to cite the packages
- `source/references.bib`: bibliography used by `:cite:` roles in the documentation
- `source/_templates/versions.html`: version menu, filled from the published `versions.json`
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
