import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { readCompose } from "../scripts/compose";

const { document } = readCompose("apps/rclone-manager");
const temporaryDirectories: string[] = [];
afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) fs.rmSync(directory, { recursive: true });
});

const bootstrap = () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "rclone-manager-bootstrap-"));
  temporaryDirectories.push(directory);
  const script = document.services["rclone-manager"].command[0].replaceAll("/data", directory).replace("exec /usr/local/bin/entrypoint.sh", "exit 0");
  const run = () => {
    const result = spawnSync("/bin/bash", ["-c", script], { encoding: "utf8" });
    expect(result.status).toBe(0);
  };
  return { directory, run, connectionPath: path.join(directory, "connections.json") };
};

describe("RClone Manager host bootstrap", () => {
  test("first startup selects the external backend without overriding its host config or copying secrets", () => {
    const { run, connectionPath } = bootstrap();
    run();
    const connections = JSON.parse(fs.readFileSync(connectionPath, "utf8"));
    expect(connections._active).toBe("Host rclone");
    const active = connections[connections._active];
    expect(active.is_local).toBe(false);
    expect(active.host).toBe("rclone-host-bridge");
    expect(active.port).toBe(5572);
    expect(active.config_path).toBeUndefined();
    expect(active.username).toBeUndefined();
    expect(active.password).toBeUndefined();
    expect(fs.statSync(connectionPath).mode & 0o777).toBe(0o600);
  });

  test("restart preserves user-selected backend and additional connections byte for byte", () => {
    const { run, connectionPath } = bootstrap();
    run();
    const saved = '{"_active":"Another host","Another host":{"is_local":false,"host":"nas","port":9000}}\n';
    fs.writeFileSync(connectionPath, saved);
    run();
    expect(fs.readFileSync(connectionPath, "utf8")).toBe(saved);
  });

  test("only Manager is routed and host credentials stay in the socket bridge", () => {
    const manager = document.services["rclone-manager"];
    const bridge = document.services["rclone-host-bridge"];
    expect(manager["x-runtipi"]).toEqual({ is_main: true, internal_port: 8080 });
    expect(manager.depends_on["rclone-host-bridge"].condition).toBe("service_healthy");
    expect(manager.environment.HOST_RC_PASS).toBeUndefined();
    expect(bridge["x-runtipi"]).toBeUndefined();
    expect(bridge.ports).toBeUndefined();
    expect(bridge.volumes).toEqual([{ type: "bind", source: "/run/rclone", target: "/run/rclone", read_only: true }]);
    for (const service of [manager, bridge]) {
      expect(service.devices).toBeUndefined();
      expect(service.privileged).toBeUndefined();
    }
  });
});
