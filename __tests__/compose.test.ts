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

test("Renovate discovers every native YAML image", () => {
  const config = JSON.parse(fs.readFileSync("renovate.json", "utf8"));
  const appDirectories = fs.readdirSync("apps").filter((name) => fs.existsSync(path.join("apps", name, "docker-compose.yml")));

  for (const appDirectory of appDirectories) {
    const composePath = `apps/${appDirectory}/docker-compose.yml`;
    const manager = config.customManagers.find((item: { managerFilePatterns: string[] }) =>
      item.managerFilePatterns.some((pattern) => {
        const expression = pattern.startsWith("/") && pattern.endsWith("/") ? pattern.slice(1, -1) : pattern;
        return new RegExp(expression).test(composePath);
      }),
    );
    expect(manager).toBeDefined();

    const source = fs.readFileSync(composePath, "utf8");
    const matches = [...source.matchAll(new RegExp(manager.matchStrings[0], "g"))];
    const discoveredImages = matches.map((match) => `${match.groups?.depName}:${match.groups?.currentValue}`).sort();
    const { document } = readCompose(path.join(process.cwd(), "apps", appDirectory));
    const composeImages = Object.values(document.services)
      .map((service) => (service as { image: string }).image)
      .sort();
    expect(discoveredImages).toEqual(composeImages);
  }
});

test("native Compose files avoid runtime variables omitted from generated app.env files", () => {
  const appDirectories = fs.readdirSync("apps").filter((name) => fs.existsSync(path.join("apps", name, "docker-compose.yml")));

  for (const appDirectory of appDirectories) {
    const source = fs.readFileSync(path.join("apps", appDirectory, "docker-compose.yml"), "utf8");
    expect(source).not.toMatch(/\$\{(?:RUNTIPI_MEDIA_DIR|UID|GID)\}/);
  }
});
