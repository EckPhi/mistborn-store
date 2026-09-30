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


if __name__ == "__main__":
    unittest.main()
