"""Opt-in three-service acceptance. Run prepare, restart services, then verify.

Requires installed mlflow==3.16.1, Coder CLI v2.36.6 and authenticated CLI state.
Secrets come from environment. Never print responses or command stderr on failure.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import uuid


def reachable(url, path):
    with urllib.request.urlopen(url.rstrip('/') + path, timeout=15) as response:
        assert response.status == 200


def ssh(workspace, command):
    return subprocess.run(['coder', 'ssh', workspace, '--', 'bash', '-s'],
                          input=command, text=True, capture_output=True, timeout=900,
                          check=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'verify'])
    parser.add_argument('--workspace', default='dev')
    parser.add_argument('--state', type=Path, default=Path('platform-acceptance.json'))
    args = parser.parse_args()
    for key, path in [('CODER_URL', '/healthz'), ('OMNIGENT_URL', '/health'),
                      ('MLFLOW_TRACKING_URI', '/health')]:
        reachable(os.environ[key], path)
    from mlflow import MlflowClient
    client = MlflowClient()
    if args.phase == 'prepare':
        marker = uuid.uuid4().hex
        # Real clone from a small Git fixture, then a deterministic mock-agent edit.
        script = '''set -euo pipefail
mkdir -p ~/workspaces/platform-acceptance-MARKER
cd ~/workspaces/platform-acceptance-MARKER
git init --bare remote.git >/dev/null
git clone remote.git project >/dev/null 2>&1
cd project
cat > CMakeLists.txt <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(smoke LANGUAGES CXX)
enable_testing()
add_executable(smoke main.cpp)
add_test(NAME smoke COMMAND smoke)
CMAKE
printf 'int main(){return 0;}\\n' > main.cpp
git add .
git -c user.name=Acceptance -c user.email=acceptance@example.invalid commit -m fixture >/dev/null
printf '// mock agent reviewed this file\\n' >> main.cpp
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
git diff --exit-code >/dev/null && exit 1
printf 'MARKER' > ~/platform-acceptance-MARKER
python3 --version; node --version; git --version
codex --version; claude --version; opencode --version; omnigent --version
'''.replace('MARKER', marker)
        ssh(args.workspace, script)
        experiment = client.create_experiment('platform-acceptance-' + marker)
        run = client.create_run(experiment)
        run_id = run.info.run_id
        client.log_param(run_id, 'action', 'mock-agent-cpp-build')
        client.log_metric(run_id, 'tests_passed', 1)
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'result.txt'
            artifact.write_text(marker)
            client.log_artifact(run_id, str(artifact))
        client.set_terminated(run_id)
        args.state.write_text(json.dumps({'marker': marker, 'run_id': run_id,
                                         'workspace': args.workspace}))
        args.state.chmod(0o600)
        print('Prepared workspace fixture and MLflow run. Restart each app independently, then run verify.')
    else:
        state = json.loads(args.state.read_text())
        marker = state['marker']
        assert len(marker) == 32 and all(c in '0123456789abcdef' for c in marker)
        assert ssh(state['workspace'], f'cat ~/platform-acceptance-{marker}') == marker
        ssh(state['workspace'], f'cd ~/workspaces/platform-acceptance-{marker}/project && ctest --test-dir build --output-on-failure')
        run = client.get_run(state['run_id'])
        assert run.data.params['action'] == 'mock-agent-cpp-build'
        assert run.data.metrics['tests_passed'] == 1
        with tempfile.TemporaryDirectory() as directory:
            path = client.download_artifacts(state['run_id'], 'result.txt', directory)
            assert Path(path).read_text() == marker
        print('Workspace files/build and MLflow metadata/artifact survived restarts; all services reachable.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Acceptance failed ({type(error).__name__}); inspect services privately.')
        raise SystemExit(1)
