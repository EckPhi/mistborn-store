import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('lifecycle', ROOT / 'apps/coder-dev/bootstrap/lifecycle.py')
lifecycle = importlib.util.module_from_spec(spec); spec.loader.exec_module(lifecycle)
spec = importlib.util.spec_from_file_location('bootstrap_save', ROOT / 'apps/coder-dev/bootstrap/bootstrap.py')
bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)


class API:
    def __init__(self):
        self.items = {key: {'id': key, 'latest_build': {'id': 'initial-' + key, 'status': status, 'template_version_id': 'selected-version-' + key}} for key, status in [('one','running'), ('two','running'), ('three','stopped')]}
        self.calls = []
        self.fail_stop = False
        self.slow_start = False

    def request(self, method, path, body=None):
        if path.startswith('/api/v2/workspaces?'): return 200, {'workspaces': list(self.items.values())}
        key = path.split('/')[4]
        if key not in self.items: return 404, None
        workspace = self.items[key]
        if method == 'GET': return 200, workspace
        self.calls.append((key, body.copy()))
        if body['transition'] == 'stop' and self.fail_stop: return 500, None
        status = 'stopped' if body['transition'] == 'stop' else ('starting' if self.slow_start else 'running')
        workspace['latest_build'] = {'id': body['transition'] + '-' + key, 'status': status, 'template_version_id': body['template_version_id']}
        return 201, workspace['latest_build']


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.journal = Path(self.temp.name) / 'lifecycle.json'
        self.api = API()
        self.output = io.StringIO(); self.redirect = contextlib.redirect_stdout(self.output); self.redirect.__enter__(); self.addCleanup(self.redirect.__exit__, None, None, None)

    def stop(self): lifecycle.stop(self.api, self.journal, bootstrap.save, timeout=1, delay=0)
    def resume(self): lifecycle.resume(self.api, self.journal, bootstrap.save)

    def test_stops_running_only_and_resumes_original_template_versions(self):
        self.stop()
        self.assertEqual(set(json.loads(self.journal.read_text())['workspaces']), {'one', 'two'})
        self.assertTrue(all(x['latest_build']['status'] == 'stopped' for x in self.api.items.values()))
        self.resume(); self.resume()
        self.assertEqual(self.api.items['one']['latest_build']['status'], 'running')
        self.assertEqual(self.api.items['three']['latest_build']['status'], 'stopped')
        self.assertEqual(len(self.api.calls), 4)
        for key, body in self.api.calls: self.assertEqual(body['template_version_id'], 'selected-version-' + key)
        self.assertEqual(self.journal.stat().st_mode & 0o777, 0o600)

    def test_stop_failure_retains_resume_intent_and_reports_failure(self):
        self.api.fail_stop = True
        with self.assertRaises(lifecycle.LifecycleError): self.stop()
        self.assertEqual(set(json.loads(self.journal.read_text())['workspaces']), {'one', 'two'})

    def test_start_is_not_duplicated_after_helper_restart(self):
        self.stop(); self.api.slow_start = True; self.resume(); self.resume()
        self.assertEqual(len(self.api.calls), 4)
        self.api.items['one']['latest_build']['status'] = 'running'; self.api.items['two']['latest_build']['status'] = 'running'
        self.resume()
        self.assertEqual(json.loads(self.journal.read_text())['workspaces'], {})

    def test_deleted_workspace_is_not_recreated(self):
        self.stop(); del self.api.items['one']; self.resume()
        self.assertFalse(any(key == 'one' and body['transition'] == 'start' for key, body in self.api.calls))

    def test_user_stop_after_resume_is_preserved(self):
        self.stop(); self.api.slow_start = True; self.resume()
        self.api.items['one']['latest_build'].update(status='stopped', id='manual-stop')
        self.resume()
        self.assertEqual(self.api.items['one']['latest_build']['status'], 'stopped')
        self.assertEqual(len(self.api.calls), 4)

    def test_shutdown_during_build_requires_manual_safety_check(self):
        self.api.items['one']['latest_build']['status'] = 'starting'
        with self.assertRaises(lifecycle.LifecycleError): self.stop()
        self.assertEqual(self.api.calls, [])

class SignalTests(unittest.TestCase):
    def test_sigterm_runs_workspace_stop_before_process_exit(self):
        import os
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'state').mkdir(); (root / 'tmp').mkdir()
            (root / 'state/state.json').write_text(json.dumps({'user_id': 'admin', 'session_token': 'fixture-session'}))
            script = root / 'signal-test.py'
            script.write_text(f'''
import sys, json
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'apps/coder-dev/bootstrap')!r})
sys.path.insert(0, {str(ROOT / 'tests/coder-dev')!r})
import bootstrap, test_lifecycle
RealPath = Path
root = RealPath({temporary!r})
bootstrap.Path = lambda value: root / str(value).lstrip('/')
api = test_lifecycle.API()
original = api.request
def request(method, path, body=None):
    if path == '/api/v2/users/me': return 200, {{'id': 'admin'}}
    result = original(method, path, body)
    (root / 'calls.json').write_text(json.dumps(api.calls))
    return result
api.request = request
bootstrap.API = lambda url: api
bootstrap.run = lambda *args, **kwargs: None
bootstrap.main()
''')
            with (root / 'logs').open('w') as logs:
                process = subprocess.Popen(['python3', str(script)], env={**os.environ, 'CODER_URL': 'http://fixture.test'}, stdout=logs, stderr=logs)
                try:
                    deadline = time.monotonic() + 5
                    while not (root / 'tmp/ready').exists() and time.monotonic() < deadline and process.poll() is None: time.sleep(0.01)
                    self.assertTrue((root / 'tmp/ready').exists(), (root / 'logs').read_text())
                    process.terminate()
                    self.assertEqual(process.wait(timeout=5), 0, (root / 'logs').read_text())
                    calls = json.loads((root / 'calls.json').read_text())
                    self.assertEqual({key for key, body in calls}, {'one', 'two'})
                    self.assertTrue(all(body['transition'] == 'stop' for key, body in calls))
                    self.assertFalse((root / 'tmp/ready').exists())
                finally:
                    if process.poll() is None: process.kill(); process.wait()
