"""Write the coverage badges of the packages, published on the gh-pages branch.

Each package's coverage is read from ``coverage-<package>.json``, written by
``pytest --cov=<package> --cov-report=json:coverage-<package>.json``. Each
badge is written to ``<badges directory>/<package>.json`` in the format of the
shields.io endpoint badge (https://shields.io/badges/endpoint-badge).

Usage: ``python tests/write_coverage_badges.py <badges directory> <package>...``
"""

import json
import sys
from pathlib import Path

# Lowest coverage (in percent) of each badge color
COLORS = [(90, "brightgreen"), (75, "green"), (60, "yellow"), (0, "red")]

badges = Path(sys.argv[1])
badges.mkdir(parents=True, exist_ok=True)

for package in sys.argv[2:]:
    totals = json.loads(Path(f"coverage-{package}.json").read_text())["totals"]
    percent = round(totals["percent_covered"])
    color = next(color for threshold, color in COLORS if percent >= threshold)
    badge = {"schemaVersion": 1, "label": f"{package} coverage", "message": f"{percent}%", "color": color}
    (badges / f"{package}.json").write_text(json.dumps(badge) + "\n")
    print(f"{package}: {percent}% ({color})")
