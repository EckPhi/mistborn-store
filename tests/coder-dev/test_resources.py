"""Plan the actual resource-limit expressions with the pinned Docker provider."""

import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import unittest


TEMPLATE = Path(__file__).resolve().parents[2] / "apps/coder-dev/template"
TERRAFORM = shutil.which(os.environ.get("TERRAFORM", "terraform"))


class DockerPing(http.server.BaseHTTPRequestHandler):
    # Provider configuration only needs ping; planning creates no containers.
    def do_GET(self):
        if self.path != "/_ping":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("API-Version", "1.41")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


@unittest.skipUnless(TERRAFORM, "Terraform required; installed by repository CI")
class ResourceLimitTests(unittest.TestCase):
    def test_provider_plans_unlimited_and_limited_resources(self):
        source = (TEMPLATE / "main.tf").read_text()
        limits = []
        for field in ("cpu_quota", "cpu_period", "memory"):
            expression = re.search(rf"^\s*{field}\s*=\s*(.+)$", source, re.M).group(1)
            expression = expression.replace("data.coder_parameter.cpu.value", "var.cpu")
            expression = expression.replace("data.coder_parameter.memory.value", "var.memory")
            limits.append(f"  {field} = {expression}")
        version = re.search(
            r'source\s*=\s*"kreuzwerker/docker"\s+version\s*=\s*"([^"]+)"',
            (TEMPLATE / "versions.tf").read_text(),
        ).group(1)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DockerPing)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="coder-resource-plan-") as directory:
                path = Path(directory)
                shutil.copyfile(TEMPLATE / ".terraform.lock.hcl", path / ".terraform.lock.hcl")
                (path / "main.tf").write_text(
                    'terraform {\n  required_providers {\n'
                    f'    docker = {{ source = "kreuzwerker/docker", version = "{version}" }}\n'
                    '  }\n}\n'
                    f'provider "docker" {{ host = "tcp://127.0.0.1:{server.server_port}" }}\n'
                    'variable "cpu" { type = number }\n'
                    'variable "memory" { type = number }\n'
                    'resource "docker_container" "workspace" {\n'
                    '  name = "coder-resource-regression"\n  image = "test"\n'
                    + "\n".join(limits) + "\n}\n"
                )

                def terraform(*args):
                    return subprocess.run(
                        [TERRAFORM, f"-chdir={directory}", *args],
                        capture_output=True, text=True, timeout=120,
                    )

                init_args = ["init", "-backend=false", "-input=false", "-no-color"]
                if os.environ.get("CODER_TERRAFORM_PLUGIN_DIR"):
                    init_args.append(f"-plugin-dir={os.environ['CODER_TERRAFORM_PLUGIN_DIR']}")
                init = terraform(*init_args)
                self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
                for cpu, memory, quota in ((0, 0, 0), (0.5, 512, 50000), (2, 2048, 200000)):
                    with self.subTest(cpu=cpu, memory=memory):
                        plan = terraform(
                            "plan", "-refresh=false", "-input=false", "-no-color",
                            f"-var=cpu={cpu}", f"-var=memory={memory}", "-out=plan",
                        )
                        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
                        shown = terraform("show", "-json", "plan")
                        self.assertEqual(shown.returncode, 0, shown.stderr)
                        values = json.loads(shown.stdout)["planned_values"]["root_module"]["resources"][0]["values"]
                        self.assertEqual(values["cpu_quota"], quota)
                        self.assertEqual(values["cpu_period"], 100000)
                        self.assertEqual(values["memory"], memory)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


    def test_isolated_docker_plans_start_stop_and_disable(self):
        # Use the maintained resource blocks and real provider, replacing only
        # Coder API inputs. No containers are created by this plan regression.
        source = (TEMPLATE / "main.tf").read_text().split('resource "docker_image" "development" {', 1)[1]
        source = 'resource "docker_image" "development" {' + source
        replacements = {
            'data.coder_workspace.me.start_count': 'var.start_count',
            'data.coder_workspace.me.id': 'var.workspace_id',
            'data.coder_workspace.me.name': 'var.workspace_name',
            'data.coder_parameter.docker_development.value': 'var.docker_development',
            'data.coder_parameter.ai_agents.value': '"false"',
            'data.coder_parameter.cpu.value': '"0"',
            'data.coder_parameter.memory.value': '"0"',
            'data.coder_provisioner.me.arch': '"amd64"',
            'coder_agent.main.init_script': '"sleep infinity"',
            'coder_agent.main.token': 'var.agent_token',
        }
        for original, replacement in replacements.items():
            source = source.replace(original, replacement)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DockerPing)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="coder-docker-plan-") as directory:
                path = Path(directory)
                shutil.copyfile(TEMPLATE / ".terraform.lock.hcl", path / ".terraform.lock.hcl")
                shutil.copytree(TEMPLATE / 'image', path / 'image')
                providers = (TEMPLATE / "versions.tf").read_text()
                version = re.search(r'version\s*=\s*"([^"]+)"', providers.split('docker = {')[1]).group(1)
                (path / "main.tf").write_text(
                    'terraform {\n  required_providers {\n'
                    f'    docker = {{ source = "kreuzwerker/docker", version = "{version}" }}\n'
                    '  }\n}\n'
                    f'provider "docker" {{ host = "tcp://127.0.0.1:{server.server_port}" }}\n'
                    'variable "start_count" { type = number }\n'
                    'variable "docker_development" { type = string }\n'
                    'variable "workspace_id" { default = "regression-id" }\n'
                    'variable "workspace_name" { default = "regression" }\n'
                    'variable "agent_token" { default = "test-token" }\n'
                    'variable "development_stack" { default = "general" }\n'
                    'locals {\n  root = "/test/workspaces/${var.workspace_id}"\n'
                    '  cache = "/test/caches/${var.workspace_id}"\n  image_hash = "test"\n}\n'
                    + source
                )

                def terraform(*args):
                    result = subprocess.run([TERRAFORM, f"-chdir={directory}", *args],
                                            capture_output=True, text=True, timeout=120)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return result.stdout

                init_args = ["init", "-backend=false", "-input=false", "-no-color"]
                if os.environ.get("CODER_TERRAFORM_PLUGIN_DIR"):
                    init_args.append(f"-plugin-dir={os.environ['CODER_TERRAFORM_PLUGIN_DIR']}")
                terraform(*init_args)
                for enabled, started in ((True, 1), (True, 0), (False, 1), (False, 0)):
                    with self.subTest(enabled=enabled, started=started):
                        terraform("plan", "-refresh=false", "-input=false", "-no-color",
                                  f"-var=docker_development={str(enabled).lower()}",
                                  f"-var=start_count={started}", "-out=plan")
                        plan = json.loads(terraform("show", "-json", "plan"))
                        resources = {r['address']: r['values'] for r in
                                     plan['planned_values'].get('root_module', {}).get('resources', [])}
                        volumes = [r for r in resources if r.startswith('docker_volume.')]
                        self.assertEqual(len(volumes), 2 if enabled else 0)
                        containers = [r for r in resources if r.startswith('docker_container.')]
                        self.assertEqual(len(containers), (3 if enabled else 1) if started else 0)
                        if not started:
                            self.assertEqual(len(resources), 2 if enabled else 0)
                            continue
                        workspace = resources['docker_container.workspace[0]']
                        self.assertNotIn('/var/run/docker.sock', str(workspace['volumes']))
                        self.assertFalse(workspace['privileged'])
                        self.assertFalse(workspace['ports'])
                        if not enabled:
                            self.assertEqual(workspace['network_mode'], 'bridge')
                            self.assertEqual(workspace['hostname'], 'regression')
                            self.assertNotIn('DOCKER_HOST=', ' '.join(workspace['env']))
                            continue
                        sidecar = resources['docker_container.docker_development[0]']
                        self.assertTrue(sidecar['privileged'])
                        self.assertEqual(sidecar['user'], '1000:1000')
                        self.assertFalse(sidecar['ports'])
                        self.assertTrue(sidecar['wait'])
                        self.assertEqual(sidecar['command'], ['dockerd', '--host=unix:///run/user/1000/docker.sock'])
                        self.assertIn('DOCKER_HOST=unix:///docker-socket/docker.sock', workspace['env'])
                        self.assertFalse(workspace['host'])
                        self.assertIsNone(workspace.get('hostname'))
                        shared = ['/home/coder', '/workspaces', '/cache']
                        mounts = lambda container: {v['container_path']: v['host_path'] for v in container['volumes']}
                        for mount in shared:
                            self.assertEqual(mounts(workspace)[mount], mounts(sidecar)[mount])
                        initializer = resources['docker_container.docker_permissions[0]']
                        self.assertTrue(initializer['attach'])
                        self.assertFalse(initializer['must_run'])
                        self.assertEqual(initializer['network_mode'], 'none')
                        expression = plan['configuration']['root_module']['resources']
                        workspace_config = next(r for r in expression if r['address'] == 'docker_container.workspace')
                        self.assertIn('docker_container.docker_development[0].id',
                                      workspace_config['expressions']['network_mode']['references'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
