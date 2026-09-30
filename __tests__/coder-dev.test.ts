import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { readCompose } from "../scripts/compose";

const root = "apps/coder-dev";
const { document } = readCompose(root);
const services = document.services;

describe("Coder development deployment", () => {
  test("builds and runs the general image as coder in CI", () => {
    if (!process.env.CI) return;
    const build = spawnSync("docker", [
      "build", "--target", "general", "--build-arg", "ENABLE_AI_AGENTS=true",
      "-t", "coder-general-smoke", `${root}/template/image`,
    ], { encoding: "utf8", timeout: 3_300_000 });
    if (build.status !== 0) console.error(build.stderr || build.stdout);
    expect(build.status).toBe(0);
    const smoke = spawnSync("docker", [
      "run", "--rm", "--user", "1000:1000", "--entrypoint", "/bin/sh",
      "coder-general-smoke", "-ec",
      `test "$HOME" = /home/coder
       codex --version && claude --version && omp --version && vibe --version
       vibe-acp --help >/dev/null
       git --version && python3 --version && node --version
       cmake --version && ninja --version && zsh --version && tmux -V
       test -f /opt/oh-my-zsh/oh-my-zsh.sh
       test -f /opt/oh-my-zsh/custom/themes/powerlevel10k/powerlevel10k.zsh-theme
       agent-info`,
    ], { encoding: "utf8", timeout: 300_000 });
    if (smoke.status !== 0) console.error(smoke.stderr || smoke.stdout);
    expect(smoke.status).toBe(0);
  }, 3_600_000);
  test("packages the maintained runtime without drift", () => {
    const result = spawnSync("python3", ["-c", "import runpy; x=runpy.run_path('scripts/coder-dev/package.py'); print(x['render'](), end='')"], {
      encoding: "utf8",
    });
    expect(result.status).toBe(0);
    expect(result.stdout).toBe(fs.readFileSync(`${root}/docker-compose.yml`, "utf8"));
  });
  test("runs bootstrap, lifecycle and provider-plan regression scenarios", () => {
    const result = spawnSync("python3", ["-m", "unittest", "discover", "-s", "tests/coder-dev"], {
      encoding: "utf8",
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    });
    if (result.status !== 0) console.error(result.stderr);
    expect(result.status).toBe(0);
  }, 180000);
  test("routes only Coder and gates startup on readiness", () => {
    expect(services["coder-dev"]["x-runtipi"]).toEqual({ is_main: true, internal_port: 7080 });
    expect(services["coder-dev"].depends_on["coder-dev-postgres"].condition).toBe("service_healthy");
    expect(services["coder-dev"].depends_on["coder-dev-assets"].condition).toBe("service_healthy");
    expect(services["coder-dev-bootstrap"].depends_on["coder-dev"].condition).toBe("service_healthy");
    expect(services["coder-dev-assets"].network_mode).toBe("none");
    for (const [name, service] of Object.entries(services) as [string, Record<string, unknown>][]) {
      expect(service.ports).toBeUndefined();
      expect(service.privileged).toBeUndefined();
      if (name !== "coder-dev-assets") expect(service.network_mode).toBeUndefined();
    }
  });
  test("keeps socket access in the control plane and admin secrets in bootstrap", () => {
    expect(services["coder-dev"].volumes).toContain("/var/run/docker.sock:/var/run/docker.sock");
    for (const name of ["coder-dev-bootstrap", "coder-dev-postgres", "coder-dev-assets"]) {
      expect(services[name].volumes.join(" ")).not.toContain("docker.sock");
    }
    expect(Object.keys(services["coder-dev"].environment).join(" ")).not.toContain("ADMIN_PASSWORD");
    expect(services["coder-dev-bootstrap"].user).toBe("1000:1000");
    expect(services["coder-dev"].environment.CODER_TELEMETRY_ENABLE).toBe("false");
    // biome-ignore lint/suspicious/noTemplateCurlyInString: Verify literal interpolation placeholders.
    expect(services["coder-dev"].environment.CODER_ACCESS_URL).toBe("${APP_PROTOCOL}://${APP_DOMAIN}");
  });
  test("pins all deployment images and uses an unused store port", () => {
    for (const service of Object.values(services) as { image: string }[]) {
      expect(service.image).toMatch(/:[v]?\d+\.\d+(?:\.\d+)?/);
      expect(service.image).not.toContain(":latest");
    }
    const config = JSON.parse(fs.readFileSync(`${root}/config.json`, "utf8"));
    expect(config.version).toBe(services["coder-dev"].image.split(":").pop());
    for (const app of fs.readdirSync("apps")) {
      if (app === "coder-dev" || !fs.existsSync(`apps/${app}/config.json`)) continue;
      expect(JSON.parse(fs.readFileSync(`apps/${app}/config.json`, "utf8")).port).not.toBe(config.port);
    }
  });
  test("uses persistent host paths independent of Terraform deletion", () => {
    const template = fs.readFileSync(`${root}/template/main.tf`, "utf8");
    expect(template).not.toMatch(/resource "docker_volume"/);
    // biome-ignore lint/suspicious/noTemplateCurlyInString: Verify literal interpolation placeholders.
    expect(template).toContain("${var.data_root}/workspaces/${data.coder_workspace.me.id}");
    // biome-ignore lint/suspicious/noTemplateCurlyInString: Verify literal interpolation placeholders.
    expect(template).toContain("${var.data_root}/caches/${data.coder_workspace.me.id}");
    expect(template).toContain('data.coder_parameter.host_docker.value == "true" ? [1] : []');
    expect(template).toMatch(/name\s*= "host_docker"[\s\S]*?default\s*= "false"/);
    expect(fs.readFileSync(`${root}/bootstrap/server.sh`, "utf8")).toContain("exec su -p");
  });
});
