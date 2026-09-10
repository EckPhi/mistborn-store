import { afterEach, describe, expect, test } from "bun:test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { readCompose } from "../scripts/compose";

const directories: string[] = [];
const fixture = (text: string) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "store-compose-test-"));
  directories.push(directory);
  fs.writeFileSync(path.join(directory, "docker-compose.yml"), text);
  return directory;
};
afterEach(() => {
  for (const directory of directories.splice(0)) fs.rmSync(directory, { recursive: true });
});
const valid =
  "x-runtipi:\n  schema_version: 2\nservices:\n  web:\n    image: example/app:1.0.0\n    x-runtipi:\n      is_main: true\n      internal_port: 8080\n";

describe("Compose source selection and YAML validation", () => {
  test("accepts native Compose options with Runtipi metadata", () => {
    const directory = fixture(`${valid}    tmpfs:\n      - /tmp:size=1m\n`);
    expect(readCompose(directory).document.services.web.tmpfs).toEqual(["/tmp:size=1m"]);
  });
  test("rejects ambiguous JSON and YAML sources", () => {
    const directory = fixture(valid);
    fs.writeFileSync(path.join(directory, "docker-compose.json"), "{}");
    expect(() => readCompose(directory)).toThrow("exactly one Compose source");
  });
  test("rejects missing Runtipi metadata", () => {
    expect(() => readCompose(fixture("services:\n  web:\n    image: example/app:1.0.0\n"))).toThrow();
  });
  test("rejects a service without its image", () => {
    expect(() => readCompose(fixture(valid.replace("    image: example/app:1.0.0\n", "")))).toThrow();
  });
  test("rejects duplicate YAML service keys", () => {
    expect(() => readCompose(fixture(`${valid}  web:\n    image: example/other:2.0.0\n`))).toThrow();
  });
  test("requires a main service", () => {
    expect(() => readCompose(fixture(valid.replace("is_main: true", "is_main: false")))).toThrow("exactly one");
  });
});

test("ERPNext images, assets mounts and startup gates stay aligned", () => {
  const { document } = readCompose(path.join(process.cwd(), "apps/erpnext"));
  const config = JSON.parse(fs.readFileSync("apps/erpnext/config.json", "utf8"));
  const services = document.services;
  const application = Object.entries(services).filter(([name]) => !["erpnext-db", "erpnext-redis-cache", "erpnext-redis-queue"].includes(name));
  expect(application).toHaveLength(9);
  for (const [name, value] of application) {
    const service = value as { image: string; tmpfs?: string[]; environment?: Record<string, string>; entrypoint?: string[] };
    expect(service.image).toBe(`eckphi/ief-bookkeeping:${config.version}`);
    if (name === "erpnext-sites-seed") {
      expect(service.tmpfs).toBeUndefined();
      expect(service.entrypoint?.at(-1)).toContain("ief-runtime-assets.py seed");
    } else {
      expect(service.environment?.IEF_RUNTIME_ASSETS).toBe("1");
      expect(service.tmpfs).toEqual(["/home/frappe/frappe-bench/sites/assets:rw,nosuid,nodev,noexec,size=1m,uid=1000,gid=1000,mode=0755"]);
    }
  }
  for (const name of ["erpnext-configurator", "erpnext-create-site"]) {
    expect(services[name].entrypoint.slice(0, 3)).toEqual(["python3", "/usr/local/bin/ief-runtime-assets.py", "run"]);
  }
  expect(services["erpnext-create-site"].entrypoint.at(-1)).toContain("bench --site frontend migrate");
  expect(services["erpnext-backend"].depends_on["erpnext-create-site"].condition).toBe("service_healthy");
});

test("Renovate discovers every native YAML image", () => {
  const config = JSON.parse(fs.readFileSync("renovate.json", "utf8"));
  const manager = config.customManagers.find((item: { fileMatch: string[] }) =>
    item.fileMatch.some((pattern) => new RegExp(pattern).test("apps/erpnext/docker-compose.yml")),
  );
  expect(manager).toBeDefined();
  const source = fs.readFileSync("apps/erpnext/docker-compose.yml", "utf8");
  const matches = [...source.matchAll(new RegExp(manager.matchStrings[0], "g"))];
  expect(matches).toHaveLength(12);
  expect(matches.filter((match) => match.groups?.depName === "eckphi/ief-bookkeeping")).toHaveLength(9);
});
