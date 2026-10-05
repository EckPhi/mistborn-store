import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bootstrap", ROOT / "apps/coder-dev/bootstrap/bootstrap.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class Coder:
    """Scenario double: supports the API routes used by bootstrap, not DB edits."""
    def __init__(self):
        self.url = "http://coder.test"
        self.token = ""
        self.user = None
        self.password = None
        self.template = None
        self.templates = {}
        self.workspace = None
        self.commands = []
        self.admin_creations = 0
        self.login_count = 0
        self.fail_push = False
        self.fail_template = None
        self.fail_create = False
        self.fail_login = False
        self.fail_startup = False
        self.valid_token = "test-session"
        self.versions = {}

    def request(self, method, path, body=None):
        if path == "/api/v2/users/first":
            if method == "GET": return (200 if self.user else 404), {}
            self.admin_creations += 1
            self.user = {"id": "admin-id"}
            self.password = body["password"]
            return 201, {"user_id": "admin-id", "organization_id": "org-id"}
        if path == "/api/v2/users/login":
            self.login_count += 1
            if self.fail_login or body['password'] != self.password: return 401, None
            return 201, {"session_token": self.valid_token}
        if self.token != self.valid_token: return 401, None
        if path == "/api/v2/users/me": return 200, self.user
        if path == "/api/v2/users/me/organizations": return 200, [{"id": "org-id"}]
        if path.startswith("/api/v2/organizations/org-id/templates/"):
            name = path.rsplit('/', 1)[1]
            template = self.template if name == 'general-development' else self.templates.get(name)
            return (200, template) if template else (404, None)
        if path.startswith("/api/v2/templates/") and '/versions/' in path:
            version = self.versions.get((path.split('/')[4], path.rsplit('/', 1)[1]))
            return (200, version) if version else (404, None)
        if path.startswith("/api/v2/templates/") and method == "PATCH":
            identifier = path.split('/')[4]
            template = self.template if identifier == 'template-id' else self.templates[identifier.removesuffix('-id')]
            if not path.endswith('/versions'): template.update(body)
            return 200, template
        if "/workspace/" in path:
            return (200, self.workspace) if self.workspace else (404, None)
        raise AssertionError((method, path))

    def cli(self, api, *args):
        self.commands.append(args)
        if args[0] == "templates":
            name = args[2]
            if self.fail_push or self.fail_template == name: raise b.BootstrapError("template failure")
            identifier = 'template-id' if name == 'general-development' else name + '-id'
            template = {"id": identifier}
            if name == 'general-development': self.template = template
            else: self.templates[name] = template
            if '--name' in args:
                self.versions[(identifier, args[args.index('--name') + 1])] = {'id': 'version-id', 'job': {'status': 'succeeded'}}
        if args[0] == "create":
            if self.fail_create: raise b.BootstrapError("workspace failure")
            self.workspace = {"id": "workspace-id", "latest_build": {"status": "running", "resources": [{"agents": [{"status": "connected", "lifecycle_state": "start_error" if self.fail_startup else "ready"}]}]}}
        if args[0] == "start":
            self.workspace["latest_build"]["status"] = "running"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.json"
        self.template = Path(self.temp.name) / "template"
        self.template.mkdir()
        (self.template / "main.tf").write_text("version-one")
        self.env = dict(CODER_DEV_ADMIN_USERNAME="testadmin", CODER_DEV_ADMIN_EMAIL="test@example.test",
                        CODER_DEV_ADMIN_PASSWORD="fictional-test-password", CODER_DEV_DATA_ROOT="/test/app-data", CODER_DEV_WORKSPACE_NAME="dev")
        self.coder = Coder()
        self.templates = {"general-development": "general"}
        self.logs = io.StringIO()

    def test_new_workspace_enables_isolated_docker(self):
        self.run_bootstrap()
        create = next(command for command in self.coder.commands if command[0] == "create")
        self.assertIn("docker_development=true", create)
        self.assertFalse(any("host_docker" in argument for argument in create))

    def run_bootstrap(self):
        with contextlib.redirect_stdout(self.logs):
            b.run(self.coder, self.path, self.template, self.env, self.coder.cli, self.templates)

    def test_fresh_install_repeated_restarts_and_secret_safe_state(self):
        self.run_bootstrap()
        for _ in range(4): self.run_bootstrap()
        self.assertEqual(self.coder.admin_creations, 1)
        self.assertEqual(sum(c[0] == 'create' for c in self.coder.commands), 1)
        self.assertEqual(sum(c[0] == 'templates' for c in self.coder.commands), 1)
        self.assertEqual(self.coder.template['default_ttl_ms'], 0)
        self.assertNotIn(self.env['CODER_DEV_ADMIN_PASSWORD'], self.logs.getvalue())
        self.assertNotIn(self.env['CODER_DEV_ADMIN_PASSWORD'], self.path.read_text())
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_upgrade_preserves_identity_and_stopped_workspace_and_source(self):
        source = Path(self.temp.name) / "source.txt"
        source.write_text("uncommitted source")
        self.run_bootstrap()
        self.coder.workspace['latest_build']['status'] = 'stopped'
        (self.template / 'main.tf').write_text('version-two')
        self.run_bootstrap()
        self.assertEqual(self.coder.workspace['latest_build']['status'], 'stopped')
        self.assertEqual(self.coder.admin_creations, 1)
        self.assertEqual(sum(c[0] == 'templates' for c in self.coder.commands), 2)
        self.assertEqual(source.read_text(), 'uncommitted source')
        self.assertFalse(any(c[0] == 'start' for c in self.coder.commands))

    def test_template_failure_resumes_without_recreating_admin(self):
        self.coder.fail_push = True
        with self.assertRaises(b.BootstrapError): self.run_bootstrap()
        self.coder.fail_push = False
        self.run_bootstrap()
        self.assertEqual(self.coder.admin_creations, 1)
        self.assertTrue(json.loads(self.path.read_text())['workspace_ready'])

    def test_workspace_creation_failure_resumes_without_duplicate_template(self):
        self.coder.fail_create = True
        with self.assertRaises(b.BootstrapError): self.run_bootstrap()
        self.coder.fail_create = False
        self.run_bootstrap()
        self.assertEqual(sum(c[0] == 'templates' for c in self.coder.commands), 1)
        self.assertEqual(self.coder.admin_creations, 1)

    def test_failed_initial_workspace_build_is_retried(self):
        self.run_bootstrap()
        state = json.loads(self.path.read_text()); state.pop('workspace_ready'); b.save(self.path, state)
        self.coder.workspace['latest_build']['status'] = 'failed'
        self.run_bootstrap()
        self.assertEqual(sum(c[0] == 'start' for c in self.coder.commands), 1)
        self.assertEqual(sum(c[0] == 'create' for c in self.coder.commands), 1)

    def test_connected_agent_startup_error_does_not_complete_bootstrap(self):
        self.coder.fail_startup = True
        with self.assertRaisesRegex(b.BootstrapError, 'startup script failed'):
            self.run_bootstrap()
        self.assertFalse(json.loads(self.path.read_text()).get('workspace_ready', False))

    def test_completed_push_before_state_write_is_reused(self):
        self.run_bootstrap()
        state = json.loads(self.path.read_text()); state['template_fingerprints'].pop('general-development'); b.save(self.path, state)
        self.run_bootstrap()
        self.assertEqual(sum(c[0] == 'templates' for c in self.coder.commands), 1)

    def test_publishes_each_stack_once_without_extra_workspaces(self):
        self.templates = b.development_templates('amd64')
        self.run_bootstrap()
        self.run_bootstrap()
        pushes = [c for c in self.coder.commands if c[0] == 'templates']
        self.assertEqual(len(pushes), 4)
        for command in pushes:
            self.assertIn('development_stack=' + self.templates[command[2]], command)
        self.assertEqual(sum(c[0] == 'create' for c in self.coder.commands), 1)
        self.assertEqual(len(json.loads(self.path.read_text())['template_fingerprints']), 4)

    def test_partial_profile_publication_resumes_without_duplicate_general(self):
        self.templates = b.development_templates('amd64')
        self.coder.fail_template = 'python-development'
        with self.assertRaises(b.BootstrapError): self.run_bootstrap()
        self.coder.fail_template = None
        self.run_bootstrap()
        self.assertEqual(sum(c[0] == 'templates' and c[2] == 'general-development' for c in self.coder.commands), 1)
        self.assertEqual(sum(c[0] == 'create' for c in self.coder.commands), 1)
        self.assertEqual(self.coder.admin_creations, 1)

    def test_failed_named_version_retry_keeps_stack_and_all_variables(self):
        self.run_bootstrap()
        state = json.loads(self.path.read_text())
        fingerprint = state['template_fingerprints'].pop('general-development')
        self.coder.versions[('template-id', 'bundle-' + fingerprint[:16])]['job']['status'] = 'failed'
        b.save(self.path, state)
        self.run_bootstrap()
        command = self.coder.commands[-1]
        self.assertNotIn('--name', command)
        self.assertIn('development_stack=general', command)
        self.assertIn('data_root=/test/app-data', command)
        self.assertIn('git_name=', command)
        self.assertIn('git_email=', command)

    def test_arm64_skips_only_flutter(self):
        with contextlib.redirect_stdout(self.logs):
            self.assertEqual(set(b.development_templates('aarch64').values()), {'general', 'python', 'rust'})

    def test_user_deleted_workspace_is_not_recreated(self):
        self.run_bootstrap()
        self.coder.workspace = None
        self.run_bootstrap()
        self.assertEqual(sum(c[0] == 'create' for c in self.coder.commands), 1)

    def test_changed_password_does_not_reset_admin(self):
        self.run_bootstrap()
        self.coder.password = 'changed-in-coder'
        self.run_bootstrap()  # existing session remains usable
        self.coder.valid_token = 'new-session'  # expired/revoked session
        with self.assertRaisesRegex(b.BootstrapError, 'login failed'): self.run_bootstrap()
        self.assertEqual(self.coder.password, 'changed-in-coder')
        self.assertEqual(self.coder.admin_creations, 1)

    def test_existing_stopped_workspace_is_adopted_without_starting(self):
        self.coder.user = {'id': 'admin-id'}; self.coder.password = self.env['CODER_DEV_ADMIN_PASSWORD']
        self.coder.workspace = {'id': 'existing', 'latest_build': {'status': 'stopped'}}
        self.run_bootstrap()
        self.assertFalse(any(c[0] in ('create', 'start') for c in self.coder.commands))

    def test_partial_restore_refuses_to_create_replacement_identity(self):
        self.run_bootstrap()
        self.coder.user = None
        with self.assertRaisesRegex(b.BootstrapError, 'Restore PostgreSQL'): self.run_bootstrap()
        self.assertEqual(self.coder.admin_creations, 1)

    def test_unexpected_http_failure_does_not_trigger_creation(self):
        original = self.coder.request
        def request(method, path, body=None):
            if path.endswith('/templates/general-development'): return 500, None
            return original(method, path, body)
        self.coder.request = request
        with self.assertRaisesRegex(b.BootstrapError, 'Template lookup'): self.run_bootstrap()
        self.assertEqual(self.coder.commands, [])



class DependencyUpdateTests(unittest.TestCase):
    def test_helper_image_bump_keeps_coder_version_and_regenerates_bundle(self):
        spec = importlib.util.spec_from_file_location('updater', ROOT / 'scripts/coder-dev/update.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); app = root / 'apps/coder-dev'; scripts = root / 'scripts/coder-dev'
            (app / 'bootstrap').mkdir(parents=True); (app / 'template').mkdir(); scripts.mkdir(parents=True)
            for file in ('server.sh', 'bootstrap.py'): (app / 'bootstrap' / file).write_text('test')
            (scripts / 'package.py').write_text((ROOT / 'scripts/coder-dev/package.py').read_text())
            source = '  coder-dev-assets:\n    image: ghcr.io/coder/coder:v2.36.6\n  coder-dev:\n    image: ghcr.io/coder/coder:v2.36.6\n  coder-dev-bootstrap:\n    image: python:3.13.15-bookworm\n# @BUNDLE@\n'
            (scripts / 'compose.template.yml').write_text(source)
            (app / 'docker-compose.yml').write_text(source.replace('3.13.15', '3.13.16'))
            (app / 'config.json').write_text(json.dumps({'version': 'v2.36.6', 'tipi_version': 1}))
            module.ROOT = root; module.APP = app; module.TEMPLATE = scripts / 'compose.template.yml'
            module.update('apps/coder-dev/docker-compose.yml')
            config = json.loads((app / 'config.json').read_text())
            self.assertEqual(config['version'], 'v2.36.6')
            self.assertEqual(config['tipi_version'], 2)
            self.assertIn('python:3.13.16-bookworm', module.TEMPLATE.read_text())
            self.assertNotIn('@BUNDLE@', (app / 'docker-compose.yml').read_text())

if __name__ == '__main__': unittest.main()
