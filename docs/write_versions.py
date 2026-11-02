"""Write the version list and the root redirect of the online documentation.

The published versions are ``stable`` (``main`` branch), ``dev`` (``dev``
branch), and one version per release tag ``vX.Y.Z``. The list is written to
``versions.json``, which is read by the version menu of every page.

Usage: ``python docs/write_versions.py <site directory>``
"""

import json
import re
import subprocess
import sys
from pathlib import Path

URL = "https://iterorganization.github.io/TSM-Anomaly-Detection"

site = Path(sys.argv[1])
site.mkdir(parents=True, exist_ok=True)

tags = subprocess.run(["git", "tag", "--list"], capture_output=True, text=True, check=True).stdout.split()
releases = sorted(
    (tag[1:] for tag in tags if re.fullmatch(r"v\d+\.\d+\.\d+", tag)),
    key=lambda version: [int(part) for part in version.split(".")],
    reverse=True,
)

versions = [{"version": version, "url": f"{URL}/{version}/"} for version in ["stable", "dev", *releases]]
(site / "versions.json").write_text(json.dumps(versions, indent=2) + "\n")
(site / "index.html").write_text('<!DOCTYPE html>\n<meta http-equiv="refresh" content="0; url=stable/">\n')
