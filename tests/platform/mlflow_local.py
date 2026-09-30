"""Real upstream MLflow auth/artifact/restart smoke using temporary SQLite.

This tests upstream behavior without Docker; PostgreSQL/RunTipi acceptance is separate.
Requires mlflow[auth,db]==3.16.1 in the invoking Python environment.
"""
import configparser
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def main():
    from mlflow import MlflowClient
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        password = secrets.token_hex(24)
        config = configparser.ConfigParser()
        config['mlflow'] = {
            'database_uri': f'sqlite:///{root}/auth.db',
            'default_permission': 'NO_PERMISSIONS',
            'admin_username': 'test-admin',
            'authorization_function': 'mlflow.server.auth:authenticate_request_basic_auth',
        }
        with (root / 'auth.ini').open('w') as stream:
            config.write(stream)
        env = dict(os.environ, MLFLOW_AUTH_CONFIG_PATH=str(root / 'auth.ini'),
                   MLFLOW_AUTH_ADMIN_PASSWORD=password,
                   MLFLOW_FLASK_SERVER_SECRET_KEY=secrets.token_hex(32),
                   MLFLOW_BACKEND_STORE_URI=f'sqlite:///{root}/tracking.db',
                   MLFLOW_DISABLE_TELEMETRY='true',
                   MLFLOW_TRACKING_USERNAME='test-admin',
                   MLFLOW_TRACKING_PASSWORD=password)
        url = f'http://127.0.0.1:{port}'
        os.environ.update({k: env[k] for k in ['MLFLOW_TRACKING_USERNAME', 'MLFLOW_TRACKING_PASSWORD']})
        client = MlflowClient(tracking_uri=url)
        args = [sys.executable, '-m', 'mlflow', 'server', '--host', '127.0.0.1',
                '--port', str(port), '--app-name', 'basic-auth', '--workers', '1',
                '--serve-artifacts', '--artifacts-destination', str(root / 'artifacts'),
                '--allowed-hosts', '127.0.0.1:*']
        log = (root / 'server.log').open('w')
        def start():
            process = subprocess.Popen(args, env=env, cwd=root, stdout=log, stderr=log,
                                       start_new_session=True)
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError('MLflow exited before readiness')
                try:
                    urllib.request.urlopen(url + '/health', timeout=1).close()
                    return process
                except Exception:
                    time.sleep(0.5)
            stop(process)
            raise RuntimeError('MLflow readiness deadline exceeded')
        def stop(process):
            import signal
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=30)
        process = start()
        try:
            experiment = client.create_experiment('restart-acceptance')
            run_id = client.create_run(experiment).info.run_id
            client.log_param(run_id, 'test', 'restart')
            client.log_metric(run_id, 'passed', 1)
            artifact = root / 'fixture.txt'
            artifact.write_text('persistent artifact')
            client.log_artifact(run_id, str(artifact))
            client.set_terminated(run_id)
            stop(process)
            # A changed bootstrap password must not reset the stored administrator.
            env['MLFLOW_AUTH_ADMIN_PASSWORD'] = secrets.token_hex(24)
            process = start()
            run = client.get_run(run_id)
            assert run.data.params['test'] == 'restart'
            assert run.data.metrics['passed'] == 1
            downloaded = client.download_artifacts(run_id, 'fixture.txt', str(root))
            assert Path(downloaded).read_text() == 'persistent artifact'
            print('MLflow real auth, run/parameter/metric/artifact and restart/password-preservation smoke passed (SQLite).')
        finally:
            if process.poll() is None:
                stop(process)
            log.close()


if __name__ == '__main__':
    main()
