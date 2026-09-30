"""Sync MLflow generated Compose and mirror the main image, including helper bumps."""
import json
from pathlib import Path
import re
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def update(package_file):
    app = 'mlflow' if 'mlflow' in package_file else 'omnigent'
    compose = ROOT / f'apps/{app}/docker-compose.yml'
    if app == 'mlflow':
        source = ROOT / 'scripts/platform/mlflow.compose.yml'
        if package_file == 'apps/mlflow/docker-compose.yml':
            pattern = r'(?m)^  ([a-z0-9-]+):\n    image: ([^\n]+)'
            images = dict(re.findall(pattern, compose.read_text()))
            source.write_text(re.sub(pattern, lambda m: f'  {m[1]}:\n    image: {images[m[1]]}', source.read_text()))
        compose.write_text(runpy.run_path(str(ROOT / 'scripts/platform/package.py'))['render']())
    main = re.search(rf'(?m)^  {app}:\n    image: [^\n]+:([^\n]+)', compose.read_text())
    if not main:
        raise ValueError('Missing main image')
    config_path = ROOT / f'apps/{app}/config.json'
    config = json.loads(config_path.read_text())
    config.update(version=main[1], tipi_version=config['tipi_version'] + 1,
                  updated_at=int(time.time() * 1000) - 1)
    config_path.write_text(json.dumps(config, indent=2) + '\n')


if __name__ == '__main__':
    update(sys.argv[1])
