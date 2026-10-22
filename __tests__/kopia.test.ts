import { describe, expect, test } from "bun:test";
import fs from "node:fs";
import { readCompose } from "../scripts/compose";

const { document } = readCompose("apps/kopia");
const service = document.services.kopia;

describe("Kopia Coder backup boundary", () => {
  test("reads the existing workspace volume without exposing host files or caches", () => {
    expect(document.volumes["workspace-data"]).toEqual({ external: true, name: "coder-dev-workspaces" });
    expect(service.volumes).toContain("workspace-data:/data/workspaces:ro");
    expect(service.volumes.join(" ")).not.toMatch(/docker\.sock|coder-dev-caches|\/var\/lib\/docker/);
    expect(service.volumes).toContain("restore-data:/restore");
    expect(service.volumes).toContain("kopia-cache:/app/cache");
    expect(service["x-runtipi"]).toEqual({ is_main: true, internal_port: 51515 });
    expect(service.ports).toBeUndefined();
    expect(service.privileged).toBeUndefined();
  });

  test("keeps authentication, stable source identity and persistent rclone credentials", () => {
    expect(service.hostname).toBe("coder-workspace-backup");
    expect(service.command).toContain("--server-username=kopia");
    // biome-ignore lint/suspicious/noTemplateCurlyInString: Verify literal Compose interpolation.
    expect(service.command).toContain("--server-password=${KOPIA_UI_PASSWORD}");
    expect(service.command.join(" ")).not.toMatch(/disable-csrf|unauthenticated/);
    expect(service.environment.RCLONE_CONFIG).toBe("/app/rclone/rclone.conf");
    // biome-ignore lint/suspicious/noTemplateCurlyInString: Verify literal Compose interpolation.
    expect(service.volumes).toContain("${APP_DATA_DIR}/rclone:/app/rclone");
  });

  test("Coder shutdown retains lifecycle handling without copying files into app-data", () => {
    const { document: coder } = readCompose("apps/coder-dev");
    const mounts = coder.services["coder-dev-bootstrap"].volumes.join(" ");
    expect(mounts).not.toMatch(/legacy-workspaces|snapshots/);
    const bootstrap = fs.readFileSync("apps/coder-dev/bootstrap/bootstrap.py", "utf8");
    expect(bootstrap).toContain("lifecycle.stop(api, journal");
    expect(bootstrap).toContain("lifecycle.resume(api, journal");
    expect(bootstrap).not.toContain("snapshot.create_snapshot");
  });
});
