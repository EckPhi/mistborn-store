#!/usr/bin/env python3
"""Embed the maintained runtime files; RunTipi installs only the Compose source."""
import base64
import gzip
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/coder-dev"


def bundle():
    archive = io.BytesIO()
    files = sorted(p for p in (APP / "bootstrap").iterdir() if p.suffix in (".sh", ".py"))
    files += sorted(p for p in (APP / "template").rglob("*") if p.is_file() and p.name != "README.md" and ".terraform" not in p.parts)
    with tarfile.open(fileobj=archive, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for path in files:
            content = path.read_bytes()
            info = tarfile.TarInfo(str(path.relative_to(APP)))
            info.size = len(content)
            info.mode = 0o755 if path.suffix == ".sh" else 0o644
            tar.addfile(info, io.BytesIO(content))
    compressed = io.BytesIO()
    # GzipFile normalizes the OS header across Python versions/platforms.
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
        stream.write(archive.getvalue())
    return base64.b64encode(compressed.getvalue()).decode()


def render():
    return (ROOT / "scripts/coder-dev/compose.template.yml").read_text().replace("@BUNDLE@", bundle())


if __name__ == "__main__":
    (APP / "docker-compose.yml").write_text(render())
