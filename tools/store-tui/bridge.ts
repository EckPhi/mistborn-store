// Reuse the store's YAML parser and authoritative validators, preserving comments.
import fs from "node:fs";
import path from "node:path";
import Ajv from "ajv";
import { isMap, parseDocument, stringify } from "yaml";

const schema = JSON.parse(fs.readFileSync(path.join(process.cwd(), "apps/app-info-schema.json"), "utf8"));
const { readCompose } = await import(path.join(process.cwd(), "scripts/compose.ts"));

const input = await Bun.stdin.json();
try {
  if (input.action === "format") {
    console.log(JSON.stringify(stringify(input.value)));
  } else if (input.action === "images") {
    const yaml = input.filename.endsWith(".yml");
    const doc = yaml ? parseDocument(input.text) : null;
    if (doc?.errors.length) throw new Error(doc.errors.map((e) => e.message).join("\n"));
    const value = yaml ? doc?.toJS() : JSON.parse(input.text);
    const services = yaml ? Object.entries(value.services).map(([name, service]) => ({ name, ...(service as object) })) : value.services;
    console.log(
      JSON.stringify(
        services.map((s: { name: string; image: string; isMain?: boolean; "x-runtipi"?: { is_main?: boolean } }) => ({
          name: s.name,
          image: s.image,
          main: yaml ? !!s["x-runtipi"]?.is_main : !!s.isMain,
        })),
      ),
    );
  } else if (input.action === "replace") {
    const source = input.filename.endsWith(".yml") ? parseDocument(input.text).toJS() : JSON.parse(input.text);
    if (source.overrides?.length || source["x-runtipi"]?.overrides?.length)
      throw new Error("Architecture overrides need manual editing and validation");
    if (input.filename.endsWith(".yml")) {
      const doc = parseDocument(input.text);
      if (doc.errors.length) throw new Error(doc.errors.map((e) => e.message).join("\n"));
      // Change scalar nodes in place; preserve native options, comments and ordering.
      const services = doc.get("services");
      if (!isMap(services)) throw new Error("Expected service map");
      for (const pair of services.items) {
        const service = pair.value;
        if (!isMap(service)) throw new Error("Service aliases/merges need manual editing");
        if (service.get("image") === input.old) service.set("image", input.image);
      }
      console.log(JSON.stringify(doc.toString()));
    } else {
      const value = JSON.parse(input.text);
      for (const service of value.services) if (service.image === input.old) service.image = input.image;
      console.log(JSON.stringify(`${JSON.stringify(value, null, 2)}\n`));
    }
  } else if (input.action === "validate") {
    const directory = input.directory;
    const config = JSON.parse(fs.readFileSync(path.join(directory, "config.json"), "utf8"));
    const validate = new Ajv({ allErrors: true, allowUnionTypes: true }).compile(schema);
    if (!validate(config)) throw new Error(JSON.stringify(validate.errors, null, 2));
    if (config.id !== input.id) throw new Error("App id must match directory name");
    for (const key of ["created_at", "updated_at"])
      if (config[key] !== undefined && config[key] >= Date.now()) throw new Error(`${key} must be in the past`);
    for (const field of config.form_fields ?? [])
      if (field.type === "random" && field.required !== false) throw new Error("Random fields must be optional");
    const { document, filename } = readCompose(directory);
    if (
      filename.endsWith(".json") &&
      document.services.filter((s: { name: string; image: string; isMain?: boolean; "x-runtipi"?: { is_main?: boolean } }) => s.isMain).length !== 1
    )
      throw new Error("Expected exactly one main service");
    for (const f of ["metadata/description.md", "metadata/logo.jpg"])
      if (!fs.statSync(path.join(directory, f)).isFile()) throw new Error(`Missing ${f}`);
    console.log(JSON.stringify("Schema and metadata validation passed"));
  } else throw new Error("Unknown action");
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}
