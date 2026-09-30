"""Configure the upstream MLflow server without putting credentials in argv."""
import configparser
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote


def configure(env, root=Path('/data')):
    secrets_file = root / 'secrets.json'
    if secrets_file.exists():
        if secrets_file.stat().st_mode & 0o077:
            raise ValueError('secrets.json must be private (mode 0600)')
        values = json.loads(secrets_file.read_text())
        allowed = {'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'MLFLOW_AUTH_ADMIN_PASSWORD'}
        if not isinstance(values, dict) or not values.keys() <= allowed or not all(isinstance(v, str) for v in values.values()):
            raise ValueError('Unsupported secret file fields')
        env.update(values)
    password = quote(env['MLFLOW_DB_PASSWORD'], safe='')
    uri = f'postgresql+psycopg2://mlflow:{password}@mlflow-postgres:5432/mlflow'
    config = configparser.ConfigParser(interpolation=None)
    config['mlflow'] = {
        'database_uri': uri,
        'default_permission': 'NO_PERMISSIONS',
        'admin_username': env['MLFLOW_ADMIN_USERNAME'],
        'authorization_function': 'mlflow.server.auth:authenticate_request_basic_auth',
    }
    root.mkdir(parents=True, exist_ok=True)
    auth = root / 'auth.ini'
    auth.write_text('')
    auth.chmod(0o600)
    with auth.open('w') as stream:
        config.write(stream)
    bucket = env.get('MLFLOW_S3_BUCKET', '').strip()
    artifacts = f's3://{bucket}/mlflow' if bucket else str(root / 'artifacts')
    if not bucket:
        (root / 'artifacts').mkdir(exist_ok=True)
    env['MLFLOW_AUTH_CONFIG_PATH'] = str(auth)
    env['MLFLOW_BACKEND_STORE_URI'] = uri
    env['MLFLOW_DISABLE_TELEMETRY'] = 'true'
    for key in ['MLFLOW_S3_ENDPOINT_URL', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']:
        if not env.get(key):
            env.pop(key, None)
    return ['mlflow', 'server', '--host', '0.0.0.0', '--port', '5000',
            '--app-name', 'basic-auth', '--serve-artifacts',
            '--artifacts-destination', artifacts,
            '--allowed-hosts', env['MLFLOW_ALLOWED_HOSTS'] + ',localhost:*,127.0.0.1:*']


def main():
    os.umask(0o077)
    try:
        args = configure(os.environ)
        # Validate storage access once; readiness HTTP checks do not mutate artifacts.
        if os.environ.get('MLFLOW_S3_BUCKET'):
            import boto3
            boto3.client('s3', endpoint_url=os.environ.get('MLFLOW_S3_ENDPOINT_URL')).head_bucket(
                Bucket=os.environ['MLFLOW_S3_BUCKET'])
    except Exception:
        print('MLflow configuration or artifact storage check failed; check installer fields and bucket access.', file=sys.stderr)
        raise SystemExit(1)
    print('MLflow configuration ready; starting authenticated tracking server.', flush=True)
    os.execvp(args[0], args)


if __name__ == '__main__':
    main()
