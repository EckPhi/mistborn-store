"""Embed MLflow startup source because RunTipi copies Compose, not adjacent scripts."""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render():
    source = (ROOT / 'apps/mlflow/runtime/server.py').read_bytes()
    encoded = base64.b64encode(source).decode()
    return (ROOT / 'scripts/platform/mlflow.compose.yml').read_text().replace('@SERVER@', encoded)


if __name__ == '__main__':
    (ROOT / 'apps/mlflow/docker-compose.yml').write_text(render())
