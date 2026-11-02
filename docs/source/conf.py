from pathlib import Path
import shutil
import sys
import os

# -- Path setup --------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
DOCS_SOURCE = Path(__file__).resolve().parent
ALGORITHMS_DIR = ROOT / "src" / "tsmadalg" / "tsmadalg" / "algorithms"
GENERATED_ALGO_DIR = DOCS_SOURCE / "algorithms" / "generated"

sys.path.insert(0, str(ROOT / "src" / "tsmadkit"))
sys.path.insert(0, str(ROOT / "src" / "tsmadalg"))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "TSM Anomaly Detection Algorithms"
copyright = '2025-2026, ITER Organization'
author = 'Joris Paret'


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
	'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
	'sphinx.ext.coverage',
	'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton',
    "sphinx_treeview",
	'sphinx_rtd_theme',
    "myst_parser",
    "sphinxcontrib.bibtex"
]
myst_enable_extensions = ["colon_fence"]

# Bibliography used by :cite: roles (or {cite} in Markdown)
bibtex_bibfiles = ["references.bib"]
bibtex_default_style = "unsrt"

# Each page numbers its own references from [1], so labels repeat across pages
suppress_warnings = ["bibtex.duplicate_label"]

templates_path = ['_templates']
exclude_patterns = []

# Function/method/attribute summary lists
autosummary_generate = True

# include __init__ methods
autoclass_content = 'both'

# sort members by the order they appear in source files
autodoc_member_order = 'bysource'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
}


# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
	'python': ('https://docs.python.org/3', None),
}


# -- Generate algorithms documentation ---------------------------------------

def generate_algorithm_docs(app):
    GENERATED_ALGO_DIR.mkdir(parents=True, exist_ok=True)

    for rst_file in GENERATED_ALGO_DIR.glob("*.rst"):
        rst_file.unlink()

    algorithm_pages = []

    for algo_dir in sorted(ALGORITHMS_DIR.iterdir()):
        if not algo_dir.is_dir():
            continue
        if algo_dir.name.startswith("_"):
            continue
        if not (algo_dir / "main.py").exists():
            continue

        algo_name = algo_dir.name
        page_path = GENERATED_ALGO_DIR / f"{algo_name}.rst"

        title = algo_name
        underline = "=" * len(title)

        content = f"""\
{title}
{underline}

.. note::

   This page is generated automatically from the ``{algo_name}`` algorithm package [#f1]_.

"""

        readme_path = algo_dir / "README.md"
        if readme_path.exists():
            readme_rel = os.path.relpath(readme_path, start=GENERATED_ALGO_DIR)

            content += f"""

Description [#f2]_
------------------

.. include:: {readme_rel}
   :parser: myst_parser.sphinx_
"""

        config_path = algo_dir / "example_config.json"
        if config_path.exists():
            config_rel = os.path.relpath(config_path, start=GENERATED_ALGO_DIR)

            content += f"""

------------
            
Example configuration [#f3]_
----------------------------

.. literalinclude:: {config_rel}
   :language: json
"""

        content += f"""

------------
        
Implementation
--------------

.. automodule:: tsmadalg.algorithms.{algo_name}.main
   :members:
   :undoc-members:
   :show-inheritance:
"""

        if readme_path.exists() and "{cite}" in readme_path.read_text(encoding="utf-8"):
            content += """

------------

References
----------

.. bibliography::
   :filter: docname in docnames
"""

        content += f"""

.. rubric:: Footnotes

.. [#f1] Source package: ``tsmadalg.algorithms.{algo_name}``
.. [#f2] This section is generated from ``src/tsmadalg/tsmadalg/algorithms/{algo_name}/README.md``.
.. [#f3] This section is generated from ``src/tsmadalg/tsmadalg/algorithms/{algo_name}/example_config.json``.
"""

        page_path.write_text(content, encoding="utf-8")
        algorithm_pages.append(algo_name)

def setup(app):
    app.connect("builder-inited", generate_algorithm_docs)