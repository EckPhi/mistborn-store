import importlib.util
from pathlib import Path
import tempfile
import unittest
import runpy
import shutil
import json

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('mlflow_server', ROOT / 'apps/mlflow/runtime/server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class MLflowConfigurationTests(unittest.TestCase):
    def env(self):
        return {'MLFLOW_DB_PASSWORD': 'secret$:/@', 'MLFLOW_ADMIN_USERNAME': 'owner',
                'MLFLOW_AUTH_ADMIN_PASSWORD': 'test-secret-password',
                'MLFLOW_ALLOWED_HOSTS': 'tracking.test,localhost:*,127.0.0.1:*'}

    def test_local_configuration_keeps_credentials_out_of_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.env()
            args = server.configure(env, Path(directory))
            self.assertNotIn('secret', ' '.join(args))
            self.assertIn('secret%24%3A%2F%40', env['MLFLOW_BACKEND_STORE_URI'])
            self.assertEqual((Path(directory) / 'auth.ini').stat().st_mode & 0o777, 0o600)
            self.assertNotIn('test-secret-password', (Path(directory) / 'auth.ini').read_text())
            self.assertIn('NO_PERMISSIONS', (Path(directory) / 'auth.ini').read_text())
            self.assertTrue((Path(directory) / 'artifacts').is_dir())

    def test_restart_preserves_local_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server.configure(self.env(), root)
            artifact = root / 'artifacts' / 'important.txt'
            artifact.write_text('keep')
            server.configure(self.env(), root)
            self.assertEqual(artifact.read_text(), 'keep')

    def test_s3_routes_artifacts_through_server(self):
        with tempfile.TemporaryDirectory() as directory:
            env = self.env() | {'MLFLOW_S3_BUCKET': 'experiments',
                                'MLFLOW_S3_ENDPOINT_URL': 'https://objects.test'}
            args = server.configure(env, Path(directory))
            self.assertIn('s3://experiments/mlflow', args)
            self.assertIn('--serve-artifacts', args)
            self.assertNotIn('--default-artifact-root', args)

    def test_private_secret_file_preserves_literal_dollars(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secrets = root / 'secrets.json'
            secrets.write_text('{"AWS_SECRET_ACCESS_KEY": "literal$secret"}')
            secrets.chmod(0o600)
            env = self.env()
            server.configure(env, root)
            self.assertEqual(env['AWS_SECRET_ACCESS_KEY'], 'literal$secret')
            secrets.chmod(0o644)
            with self.assertRaises(ValueError):
                server.configure(self.env(), root)


class UpdateTests(unittest.TestCase):
    def test_helper_bump_keeps_main_version_and_syncs_generated_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ['apps/mlflow', 'scripts/platform']:
                shutil.copytree(ROOT / path, root / path)
            generated = root / 'apps/mlflow/docker-compose.yml'
            generated.write_text(generated.read_text().replace('postgres:17.11-bookworm', 'postgres:17.12-bookworm'))
            module = runpy.run_path(str(root / 'scripts/platform/update.py'))
            original = json.loads((root / 'apps/mlflow/config.json').read_text())
            module['update']('apps/mlflow/docker-compose.yml')
            config = json.loads((root / 'apps/mlflow/config.json').read_text())
            self.assertEqual(config['version'], original['version'])
            self.assertEqual(config['tipi_version'], original['tipi_version'] + 1)
            self.assertIn('postgres:17.12-bookworm', (root / 'scripts/platform/mlflow.compose.yml').read_text())
            self.assertIn('postgres:17.12-bookworm', generated.read_text())

    def test_bridge_validates_name_and_uses_no_host_docker(self):
        bridge = runpy.run_path(str(ROOT / 'scripts/platform/task.py'))
        create, runner = bridge['commands']('agent-issue-123', 'https://omnigent.test')
        self.assertFalse(any('host_docker' in argument for argument in create))
        self.assertIn('docker_development=true', create)
        self.assertNotIn('delete', runner)
        with self.assertRaises(ValueError):
            bridge['commands']('dev', 'https://omnigent.test')


if __name__ == '__main__':
    unittest.main()
