import { describe, expect, test } from "bun:test";
import fs from "node:fs";
import path from "node:path";
import Ajv from "ajv";

import appInfoSchema from "../apps/app-info-schema.json";
import dynamicComposeSchema from "../apps/dynamic-compose-schema.json";

const ajv = new Ajv({ allErrors: true, allowUnionTypes: true });
const validateConfig = ajv.compile(appInfoSchema);
const validateCompose = ajv.compile(dynamicComposeSchema);

const appsRoot = path.join(process.cwd(), "apps");

const getApps = (): string[] => {
  return fs.readdirSync(appsRoot).filter((entry) => fs.statSync(path.join(appsRoot, entry)).isDirectory());
};

const readFile = (app: string, file: string): string | null => {
  try {
    return fs.readFileSync(path.join(appsRoot, app, file), "utf-8");
  } catch {
    return null;
  }
};

const apps = getApps();

const formatErrors = (errors: typeof validateConfig.errors): string => (errors ?? []).map((e) => `${e.instancePath || "/"} ${e.message}`).join("; ");

describe("appstore should contain apps", () => {
  test("at least one app exists", () => {
    expect(apps.length).toBeGreaterThan(0);
  });
});

describe("each app should have the required files", () => {
  const required = ["config.json", "docker-compose.json", "metadata/logo.jpg", "metadata/description.md"];

  for (const app of apps) {
    for (const file of required) {
      test(`${app} should have ${file}`, () => {
        expect(readFile(app, file)).not.toBeNull();
      });
    }
  }
});

describe("each app should have a valid config.json", () => {
  for (const app of apps) {
    test(app, () => {
      const config = JSON.parse(readFile(app, "config.json") ?? "{}");
      const valid = validateConfig(config);
      if (!valid) {
        console.error(`config.json invalid for ${app}: ${formatErrors(validateConfig.errors)}`);
      }
      expect(valid).toBe(true);
    });
  }
});

describe("each app should have a valid docker-compose.json", () => {
  for (const app of apps) {
    test(app, () => {
      const compose = JSON.parse(readFile(app, "docker-compose.json") ?? "{}");
      const valid = validateCompose(compose);
      if (!valid) {
        console.error(`docker-compose.json invalid for ${app}: ${formatErrors(validateCompose.errors)}`);
      }
      expect(valid).toBe(true);
    });
  }
});

describe("app config invariants", () => {
  const configs = apps.map((app) => ({
    app,
    config: JSON.parse(readFile(app, "config.json") ?? "{}") as {
      id?: string;
      created_at?: number;
      updated_at?: number;
      form_fields?: { type: string; required?: boolean }[];
    },
  }));

  test("each app id should be unique", () => {
    const ids = configs.map(({ config }) => config.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("each app id should match its directory name", () => {
    for (const { app, config } of configs) {
      expect(config.id).toBe(app);
    }
  });

  test("created_at / updated_at should be epoch ms in the past", () => {
    const now = Date.now();
    for (const { app, config } of configs) {
      for (const key of ["created_at", "updated_at"] as const) {
        const value = config[key];
        if (value === undefined) continue;
        if (value >= now) {
          throw new Error(`${app}: ${key} (${value}) must be before now (${now})`);
        }
      }
    }
  });

  test("random form fields should not be required", () => {
    for (const { config } of configs) {
      for (const field of config.form_fields ?? []) {
        if (field.type === "random") {
          expect(Boolean(field.required)).toBe(false);
        }
      }
    }
  });
});
