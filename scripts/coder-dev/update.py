#!/usr/bin/env python3
"""Renovate hook: keep source and bundle synchronized, version the MAIN image."""
import json
from pathlib import Path
import re
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/coder-dev"
TEMPLATE = ROOT / "scripts/coder-dev/compose.template.yml"


def update(package_file):
    # The existing YAML image manager edits the generated Compose file. Transfer
    # only its image changes back to source; never decode/edit archived files.
    if package_file == "apps/coder-dev/docker-compose.yml":
        generated = (APP / "docker-compose.yml").read_text()
        pattern = r"(?m)^  ([a-z0-9-]+):\n    image: ([^\n]+)"
        versions = dict(re.findall(pattern, generated))
        source = TEMPLATE.read_text()
        source = re.sub(pattern, lambda m: f"  {m[1]}:\n    image: {versions[m[1]]}", source)
        TEMPLATE.write_text(source)
    main = re.search(r"(?m)^  coder-dev:\n    image: ghcr.io/coder/coder:([^\n]+)", TEMPLATE.read_text())
    if not main:
        raise ValueError("Coder main image is missing from the Compose source")
    # A Coder bump must keep the seed's matching CLI/image in lockstep.
    source = re.sub(r"(?m)(    image: ghcr.io/coder/coder:)[^\n]+", lambda m: m[1] + main[1], TEMPLATE.read_text())
    TEMPLATE.write_text(source)
    config = json.loads((APP / "config.json").read_text())
    config.update(version=main[1], tipi_version=config["tipi_version"] + 1, updated_at=int(time.time() * 1000) - 1)
    (APP / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    packager = runpy.run_path(str(ROOT / "scripts/coder-dev/package.py"))
    (APP / "docker-compose.yml").write_text(packager["render"]())


if __name__ == "__main__":
    update(sys.argv[1])
