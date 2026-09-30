"""Graceful Compose shutdown/startup using Coder builds and a durable journal."""
import json
import stat
import time
from urllib.parse import quote


class LifecycleError(Exception):
    pass


def request(api, method, path, body=None, expected=(200,)):
    status, result = api.request(method, path, body)
    if status not in expected:
        raise LifecycleError(f"Workspace lifecycle request failed (HTTP {status}); stop workspaces manually before backup.")
    return status, result


def workspaces(api):
    result = []
    offset = 0
    while True:
        _, page = request(api, "GET", f"/api/v2/workspaces?limit=100&offset={offset}")
        items = page["workspaces"]
        result.extend(items)
        if len(items) < 100:
            return result
        offset += len(items)


def remove_codex_ipc_sockets(workspaces_root):
    """Remove stale Codex runtime sockets before RunTipi copies workspace data."""
    root = workspaces_root
    if not root.exists():
        return
    for workspace in root.iterdir():
        ipc = workspace / "home" / ".codex" / "ipc"
        if not ipc.is_dir():
            continue
        for entry in ipc.iterdir():
            try:
                if stat.S_ISSOCK(entry.lstat().st_mode):
                    entry.unlink()
            except FileNotFoundError:
                pass


def stop(api, journal, save, workspaces_root=None, timeout=180, delay=1):
    # Retain an earlier interrupted shutdown's resume list; never add a
    # workspace that the user had already stopped before this shutdown.
    state = json.loads(journal.read_text()) if journal.exists() else {"workspaces": {}}
    pending = {}
    for workspace in workspaces(api):
        build = workspace["latest_build"]
        if build["status"] in ("starting", "stopping", "pending", "canceling"):
            raise LifecycleError("A workspace build is still in progress. Wait for builds and stop workspaces manually before backup.")
        if build["status"] == "running":
            pending[workspace["id"]] = build["template_version_id"]
    state["workspaces"].update({key: {"version": version, "stop_build_id": None} for key, version in pending.items()})
    # Persist intent BEFORE issuing stops, so a crash cannot lose resume state.
    save(journal, state)
    for workspace_id, version in pending.items():
        _, build = request(api, "POST", f"/api/v2/workspaces/{quote(workspace_id, safe='')}/builds",
                           {"transition": "stop", "template_version_id": version}, expected=(201,))
        state["workspaces"][workspace_id]["stop_build_id"] = build["id"]
        save(journal, state)
    deadline = time.monotonic() + timeout
    while pending:
        for workspace_id in list(pending):
            status, workspace = request(api, "GET", f"/api/v2/workspaces/{quote(workspace_id, safe='')}", expected=(200, 404, 410))
            if status in (404, 410) or workspace["latest_build"]["status"] in ("stopped", "deleted"):
                del pending[workspace_id]
            elif workspace["latest_build"]["status"] in ("failed", "canceled"):
                raise LifecycleError("Workspace stop build failed; check Coder and stop workspaces manually before backup.")
        if pending:
            if time.monotonic() >= deadline:
                raise LifecycleError("Workspace shutdown timed out; verify every workspace is stopped before backup.")
            time.sleep(delay)
    if workspaces_root is not None:
        remove_codex_ipc_sockets(workspaces_root)
    print("Workspace shutdown complete; previous running state recorded", flush=True)


def resume(api, journal, save):
    if not journal.exists():
        return
    state = json.loads(journal.read_text())
    if not state["workspaces"]:
        return
    for workspace_id, record in list(state["workspaces"].items()):
        path = f"/api/v2/workspaces/{quote(workspace_id, safe='')}"
        status, workspace = request(api, "GET", path, expected=(200, 404, 410))
        if status in (404, 410) or workspace["latest_build"]["status"] == "deleted":
            del state["workspaces"][workspace_id]
            save(journal, state)
            continue
        build = workspace["latest_build"]
        if build["status"] == "stopped" and (record.get("resume_build_id") or (record.get("stop_build_id") and build["id"] != record["stop_build_id"])):
            # A newer stop was requested after our own shutdown/resume. Respect
            # that user/scheduler decision rather than restarting it again.
            del state["workspaces"][workspace_id]
            save(journal, state)
            continue
        if build["status"] == "stopped":
            # Preserve the workspace's selected template version; never upgrade
            # it implicitly as a side-effect of restarting the RunTipi app.
            _, resumed = request(api, "POST", path + "/builds", {"transition": "start", "template_version_id": record["version"]}, expected=(201,))
            record["resume_build_id"] = resumed["id"]
            save(journal, state)
            _, workspace = request(api, "GET", path)
            build = workspace["latest_build"]
        if build["status"] == "running":
            del state["workspaces"][workspace_id]
            save(journal, state)
        elif build["status"] in ("failed", "canceled"):
            raise LifecycleError("Workspace resume failed; check its build in Coder. Resume intent is retained for inspection.")
        # Starting/pending builds remain journaled until a later check confirms
        # running. Retrying startup must not submit a second start build.
    print("Previously running workspaces resumed or queued; deliberately stopped workspaces unchanged", flush=True)
