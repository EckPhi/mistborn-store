import fs from "node:fs/promises";
import path from "node:path";

const packageFile = process.argv[2];
const newVersion = process.argv[3];

type AppConfig = {
  tipi_version: number;
  version: string;
  updated_at: number;
};

const updateAppConfig = async (packageFile: string, newVersion: string) => {
  try {
    if (packageFile.startsWith("apps/coder-dev/") || packageFile === "scripts/coder-dev/compose.template.yml") {
      const { spawnSync } = await import("node:child_process");
      const result = spawnSync("python3", ["scripts/coder-dev/update.py", packageFile], { stdio: "inherit" });
      if (result.status !== 0) process.exit(result.status ?? 1);
      return;
    }
    const packageRoot = path.dirname(packageFile);
    const configPath = path.join(packageRoot, "config.json");

    const config = await fs.readFile(configPath, "utf-8");
    const configParsed = JSON.parse(config) as AppConfig;

    configParsed.tipi_version += 1;
    configParsed.version = newVersion;
    configParsed.updated_at = Date.now();

    await fs.writeFile(configPath, JSON.stringify(configParsed, null, 2));
  } catch (e) {
    console.error(`Failed to update app config, error: ${e}`);
  }
};

if (!packageFile || !newVersion) {
  console.error("Usage: node update-config.js <packageFile> <newVersion>");
  process.exit(1);
}
updateAppConfig(packageFile, newVersion);
