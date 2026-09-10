import fs from "node:fs";
import path from "node:path";
import Ajv from "ajv";
import Ajv2020 from "ajv/dist/2020";
import { parse } from "yaml";
import yamlSchema from "../apps/compose-yaml-schema.json";
import legacySchema from "../apps/dynamic-compose-schema.json";

const ajv = new Ajv({ allErrors: true, allowUnionTypes: true });
const validators = {
  "docker-compose.json": ajv.compile(legacySchema),
  "docker-compose.yml": new Ajv2020({ allErrors: true, allowUnionTypes: true }).compile(yamlSchema),
};

export const readCompose = (directory: string) => {
  const names = (Object.keys(validators) as (keyof typeof validators)[]).filter((name) => fs.existsSync(path.join(directory, name)));
  if (names.length !== 1) throw new Error(`${directory}: expected exactly one Compose source (JSON or YAML)`);
  const filename = names[0];
  if (!filename) throw new Error("Compose source missing");
  const text = fs.readFileSync(path.join(directory, filename), "utf8");
  const document = filename.endsWith(".json") ? JSON.parse(text) : parse(text);
  const validate = validators[filename];
  if (!validate(document)) {
    throw new Error(`${filename}: ${(validate.errors ?? []).map((error) => `${error.instancePath || "/"} ${error.message}`).join("; ")}`);
  }
  if (filename.endsWith(".yml")) {
    const services = Object.values(document.services) as { "x-runtipi"?: { is_main?: boolean } }[];
    if (services.filter((service) => service["x-runtipi"]?.is_main).length !== 1) {
      throw new Error(`${filename}: expected exactly one x-runtipi.is_main service`);
    }
  }
  return { filename, document };
};
