import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { readCompose } from "../scripts/compose";

describe("Modular development platform", () => {
  for (const app of ["omnigent", "mlflow"]) {
    test(`${app} has independent storage, internal DB and one route`, () => {
      const services = readCompose(`apps/${app}`).document.services;
      expect(services[app]["x-runtipi"].is_main).toBe(true);
      expect(services[app].user).toBe("1000:1000");
      expect(services[app].depends_on[`${app}-postgres`].condition).toBe("service_healthy");
      for (const service of Object.values(services) as { image: string; ports?: unknown; privileged?: unknown; volumes: string[] }[]) {
        expect(service.image).not.toContain(":latest");
        expect(service.ports).toBeUndefined();
        expect(service.privileged).toBeUndefined();
        expect(JSON.stringify(service.volumes)).not.toContain("docker.sock");
        expect(JSON.stringify(service.volumes)).not.toContain("coder-dev");
      }
    });
  }
  test("MLflow packaged startup matches maintained source", () => {
    const result = spawnSync("python3", ["-c", "import runpy; print(runpy.run_path('scripts/platform/package.py')['render'](), end='')"], {
      encoding: "utf8",
    });
    expect(result.status).toBe(0);
    expect(result.stdout).toBe(fs.readFileSync("apps/mlflow/docker-compose.yml", "utf8"));
  });
  test("MLflow configuration and restart scenarios", () => {
    const result = spawnSync("python3", ["-m", "unittest", "discover", "-s", "tests/platform"], { encoding: "utf8" });
    if (result.status !== 0) console.error(result.stderr);
    expect(result.status).toBe(0);
  });
  test("Omnigent uses account auth and disables telemetry", () => {
    const env = readCompose("apps/omnigent").document.services.omnigent.environment;
    expect(env.OMNIGENT_AUTH_PROVIDER).toBe("accounts");
    expect(env.OMNIGENT_ANALYTICS).toBe("0");
    expect(env.OMNIGENT_DISABLE_TELEMETRY).toBe("true");
  });
});
