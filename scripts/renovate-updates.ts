type RenovateLog = {
  config?: Record<string, RenovatePackage[]>;
  msg?: string;
};

type RenovatePackage = {
  packageFile: string;
  deps: RenovateDependency[];
};

type RenovateDependency = {
  depName: string;
  currentValue: string;
  updates?: RenovateUpdate[];
};

type RenovateUpdate = {
  newValue: string;
  updateType: string;
};

const jsonOutput = process.argv.includes("--json");
const input = await Bun.stdin.text();
const updates: Array<{
  packageFile: string;
  depName: string;
  currentValue: string;
  newValue: string;
  updateType: string;
}> = [];

for (const line of input.split("\n")) {
  try {
    const log = JSON.parse(line) as RenovateLog;
    if (log.msg !== "packageFiles with updates" || !log.config) continue;

    for (const packages of Object.values(log.config)) {
      for (const packageFile of packages) {
        for (const dependency of packageFile.deps) {
          for (const update of dependency.updates ?? []) {
            updates.push({
              packageFile: packageFile.packageFile,
              depName: dependency.depName,
              currentValue: dependency.currentValue,
              newValue: update.newValue,
              updateType: update.updateType,
            });
          }
        }
      }
    }
  } catch {
    // Renovate can emit non-JSON output before its structured logs start.
  }
}

if (jsonOutput) {
  for (const update of updates) console.log(JSON.stringify(update));
  process.exit(0);
}

if (updates.length === 0) {
  console.log("All app images are up to date.");
} else {
  console.log(`Found ${updates.length} update(s):`);
  for (const update of updates) {
    console.log(`- ${update.packageFile}: ${update.depName} ${update.currentValue} -> ${update.newValue} (${update.updateType})`);
  }
}
