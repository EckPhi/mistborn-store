#!/usr/bin/env python3
"""Recoverable bootstrap using the supported Coder API and matching Coder CLI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import signal
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class BootstrapError(Exception):
    pass


class API:
    def __init__(self, url, token=""):
        self.url = url.rstrip("/")
        self.token = token

    def request(self, method, path, body=None):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Coder-Session-Token"] = self.token
        data = None if body is None else json.dumps(body).encode()
        try:
            with urlopen(Request(self.url + path, data=data, headers=headers, method=method), timeout=15) as response:
                content = response.read()
                return response.status, json.loads(content) if content else None
        except HTTPError as error:
            # Do not echo response bodies: they may contain supplied credentials.
            return error.code, None
        except (URLError, TimeoutError, OSError) as error:
            raise BootstrapError("Coder is unreachable; check server health and networking.") from error


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with open(temporary, "w", opener=lambda name, flags: os.open(name, flags, 0o600)) as stream:
        json.dump(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def require(status, expected, step):
    if status not in expected:
        raise BootstrapError(f"{step} failed (HTTP {status}); inspect Coder health/settings.")


def wait_ready(api, attempts=120, delay=2):
    for _ in range(attempts):
        try:
            status, _ = api.request("GET", "/api/v2/users/first")
            if status in (200, 404):
                return status
        except BootstrapError:
            pass
        time.sleep(delay)
    raise BootstrapError("Timed out waiting for Coder readiness.")


def cli(api, *arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("CODER_DEV_ADMIN_")}
    environment.update(CODER_URL=api.url, CODER_SESSION_TOKEN=api.token, CODER_CONFIG_DIR="/tmp/coder-cli")
    try:
        subprocess.run(["/runtime/bin/coder", *arguments], env=environment, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=1800)
    except (subprocess.SubprocessError, OSError) as error:
        raise BootstrapError(f"Coder CLI {arguments[0]} failed; inspect the template/workspace build in Coder.") from error


def template_fingerprint(directory, variables):
    digest = hashlib.sha256(json.dumps(variables, sort_keys=True).encode())
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(directory)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def development_templates(architecture=None):
    import platform
    architecture = architecture or platform.machine()
    templates = {"general-development": "general", "python-development": "python", "rust-development": "rust"}
    if architecture in ("x86_64", "amd64"):
        templates["flutter-development"] = "flutter"
    else:
        print("Flutter template omitted: packaged SDK requires AMD64 Linux", flush=True)
    return templates


def publish_template(api, state, state_path, template_dir, variables, organization, name, invoke):
    fingerprints = state.setdefault("template_fingerprints", {})
    if name == "general-development" and name not in fingerprints and state.get("template_fingerprint"):
        fingerprints[name] = state["template_fingerprint"]
    fingerprint = template_fingerprint(template_dir, variables)
    template_path = f"/api/v2/organizations/{quote(organization, safe='')}/templates/{name}"
    status, template = api.request("GET", template_path)
    require(status, (200, 404), "Template lookup")
    new_template = status == 404
    if new_template or fingerprints.get(name) != fingerprint:
        args = ["templates", "push", name, "--yes", "--directory", str(template_dir), "--org", organization, "--name", "bundle-" + fingerprint[:16]]
        for key, value in variables.items():
            args.extend(["--variable", f"{key}={value}"])
        # Recover a push that succeeded just before a crash/state-file write.
        # A failed named import can be retried under a server-generated name.
        published = None
        if not new_template:
            version_status, published = api.request("GET", f"/api/v2/templates/{template['id']}/versions/bundle-{fingerprint[:16]}")
            require(version_status, (200, 404), "Template version lookup")
        if published and published.get("job", {}).get("status") == "succeeded":
            status, _ = api.request("PATCH", f"/api/v2/templates/{template['id']}/versions", {"id": published["id"]})
            require(status, (200,), "Template version activation")
        else:
            if published:
                name_index = args.index("--name")
                del args[name_index:name_index + 2]  # Keep every template variable when retrying.
            invoke(api, *args)
        status, template = api.request("GET", template_path)
        require(status, (200,), "Published template lookup")
        if new_template:
            status, _ = api.request("PATCH", f"/api/v2/templates/{template['id']}", {"default_ttl_ms": 0})
            require(status, (200,), "Initial autostop configuration")
        fingerprints[name] = fingerprint
        state["template_fingerprints"] = fingerprints
        save(state_path, state)
        print(f"Template {name} published; existing workspaces were not updated", flush=True)
    else:
        print(f"Template {name} current", flush=True)



def run(api, state_path, template_dir, environment, invoke=cli, templates=None):
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    first = wait_ready(api)
    if first == 404:
        # A missing DB with a surviving bootstrap file is a restore mismatch, not
        # an invitation to overwrite the identity of the old installation.
        if state.get("user_id"):
            raise BootstrapError("Database is empty but bootstrap state exists. Restore PostgreSQL and bootstrap together.")
        status, _ = api.request("POST", "/api/v2/users/first", {
            "username": environment["CODER_DEV_ADMIN_USERNAME"],
            "email": environment["CODER_DEV_ADMIN_EMAIL"],
            "password": environment["CODER_DEV_ADMIN_PASSWORD"],
            "trial": False,
        })
        if status == 409:
            require(wait_ready(api), (200,), "Concurrent administrator setup")
        else:
            require(status, (201,), "Administrator creation")
        print("Administrator created", flush=True)
    else:
        print("Administrator already exists", flush=True)

    api.token = state.get("session_token", "")
    status, user = api.request("GET", "/api/v2/users/me")
    if status in (401, 403) or not api.token:
        api.token = ""
        status, response = api.request("POST", "/api/v2/users/login", {
            "email": environment["CODER_DEV_ADMIN_EMAIL"],
            "password": environment["CODER_DEV_ADMIN_PASSWORD"],
        })
        if status != 201:
            raise BootstrapError("Bootstrap login failed. If the password changed in Coder, update the installer password; it will never be reset.")
        api.token = response["session_token"]
        status, user = api.request("GET", "/api/v2/users/me")
    require(status, (200,), "Bootstrap identity")
    if state.get("user_id") and state["user_id"] != user["id"]:
        raise BootstrapError("Bootstrap identity changed; refusing to create resources for another user.")
    state.update(user_id=user["id"], session_token=api.token)
    save(state_path, state)

    status, organizations = api.request("GET", "/api/v2/users/me/organizations")
    require(status, (200,), "Organization discovery")
    if not organizations:
        raise BootstrapError("Bootstrap administrator has no organization.")
    organization = state.get("organization_id", organizations[0]["id"])
    state["organization_id"] = organization
    variables = {
        "data_root": environment["CODER_DEV_DATA_ROOT"],
        "git_name": environment.get("CODER_DEV_GIT_NAME", ""),
        "git_email": environment.get("CODER_DEV_GIT_EMAIL", ""),
    }
    for template_name, stack in (templates if templates is not None else development_templates()).items():
        publish_template(api, state, state_path, template_dir,
                         {**variables, "development_stack": stack}, organization, template_name, invoke)

    name = state.get("workspace_name", environment.get("CODER_DEV_WORKSPACE_NAME", "dev"))
    if not state.get("workspace_ready"):
        path = f"/api/v2/users/{quote(user['id'], safe='')}/workspace/{quote(name, safe='')}"
        status, workspace = api.request("GET", path)
        require(status, (200, 404), "Workspace lookup")
        if status == 404:
            # If this initial workspace had already been observed, don't recreate
            # it after intentional deletion during a partially completed setup.
            if state.get("workspace_id"):
                raise BootstrapError("Initial workspace was deleted before setup finished; refusing to recreate it.")
            state.update(workspace_creation_attempted=True, workspace_name=name)
            save(state_path, state)
            invoke(api, "create", name, "--template", "general-development", "--org", organization,
                   "--yes", "--use-parameter-defaults", "--parameter", "host_docker=false",
                   "--parameter", "docker_development=false", "--parameter", "cpu=0", "--parameter", "memory=0")
            status, workspace = api.request("GET", path)
            require(status, (200,), "Created workspace lookup")
        if not state.get("workspace_creation_attempted"):
            # Never restart an existing user-owned workspace during adoption.
            state.update(workspace_ready=True, workspace_name=name, workspace_id=workspace["id"])
        else:
            state["workspace_id"] = workspace["id"]
            save(state_path, state)
            if workspace["latest_build"]["status"] in ("failed", "stopped"):
                invoke(api, "start", name, "--yes")
            for _ in range(600):
                status, workspace = api.request("GET", path)
                require(status, (200,), "Initial workspace readiness")
                build = workspace["latest_build"]
                agents = [agent for resource in build.get("resources", []) for agent in resource.get("agents", []) or []]
                if any(a.get("lifecycle_state") in ("start_error", "start_timeout") for a in agents):
                    raise BootstrapError("Initial workspace startup script failed; inspect its agent startup log in Coder.")
                if build["status"] == "running" and agents and all(a["status"] == "connected" and a.get("lifecycle_state", "ready") == "ready" for a in agents):
                    state["workspace_ready"] = True
                    break
                if build["status"] in ("failed", "canceled", "deleted"):
                    raise BootstrapError("Initial workspace build failed; inspect its build log in Coder and restart bootstrap.")
                time.sleep(2)
            else:
                raise BootstrapError("Initial workspace agent did not connect; check the access URL, DNS, TLS, and workspace logs.")
        save(state_path, state)
        print("Default workspace ready", flush=True)
    else:
        print("Default workspace already initialized; its current state was preserved", flush=True)
    print("Bootstrap complete", flush=True)


def main():
    Path("/tmp/ready").unlink(missing_ok=True)
    import lifecycle
    state_path = Path("/state/state.json")
    journal = Path("/state/lifecycle.json")
    api = API(os.environ["CODER_URL"])

    def shutdown(_signal, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        Path("/tmp/ready").unlink(missing_ok=True)
        if not state_path.exists():
            raise SystemExit(0)
        try:
            state = json.loads(state_path.read_text())
            api.token = state.get("session_token", "")
            status, user = api.request("GET", "/api/v2/users/me")
            if status != 200:
                status, login = api.request("POST", "/api/v2/users/login", {
                    "email": os.environ["CODER_DEV_ADMIN_EMAIL"],
                    "password": os.environ["CODER_DEV_ADMIN_PASSWORD"],
                })
                require(status, (201,), "Shutdown authentication")
                api.token = login["session_token"]
                status, user = api.request("GET", "/api/v2/users/me")
            require(status, (200,), "Shutdown identity")
            if user["id"] != state.get("user_id"):
                raise BootstrapError("Shutdown identity differs from bootstrap; stop workspaces manually.")
            lifecycle.stop(api, journal, save, Path("/workspaces"))
        except (BootstrapError, lifecycle.LifecycleError, KeyError, ValueError):
            print("Automatic workspace shutdown failed. Stop all workspaces manually before taking a backup.", flush=True)
            raise SystemExit(1)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    # flock releases automatically after a crash; two bootstrap instances cannot
    # race to create a template or default workspace.
    import fcntl
    with Path("/state/bootstrap.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run(api, state_path, Path("/runtime/template"), os.environ)
        try:
            lifecycle.resume(api, journal, save)
        except lifecycle.LifecycleError as error:
            print(f"Workspace resume deferred; Coder is ready and will retry: {error}", flush=True)
    Path("/tmp/ready").touch()
    while True:
        time.sleep(30)
        try:
            lifecycle.resume(api, journal, save)
        except lifecycle.LifecycleError as error:
            print(f"Workspace resume still needs attention; Coder remains ready and will retry: {error}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (BootstrapError, KeyError, ValueError) as error:
        # The exception chain and request payload are intentionally not logged.
        print(f"Bootstrap stopped: {error}", flush=True)
        raise SystemExit(1)
