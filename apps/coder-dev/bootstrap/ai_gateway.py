"""Provision personal LiteLLM keys from the trusted Coder control plane."""
import hashlib
import json
import os
from pathlib import Path
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


class GatewayError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Gateway:
    def __init__(self, url, token):
        self.url = url.rstrip("/").removesuffix("/v1")
        parts = urlsplit(self.url)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
            raise GatewayError("AI gateway URL must be an HTTP(S) base URL without credentials, query or fragment.")
        self.token = token

    def request(self, method, path, body=None):
        request = Request(self.url + path, method=method,
                          headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"},
                          data=None if body is None else json.dumps(body).encode())
        try:
            with build_opener(NoRedirect).open(request, timeout=15) as response:
                content = response.read()
                return response.status, json.loads(content) if content else None
        except HTTPError as error:
            return error.code, None
        except (URLError, TimeoutError, OSError, ValueError) as error:
            raise GatewayError("AI gateway is unreachable or returned an invalid response.") from error


def private_write(path, content):
    """Atomic writes, including when repairing an existing file's permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        path.chmod(0o600)
        return
    temporary = path.parent / (".gateway-" + secrets.token_hex(8))
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def workspace_home(root, workspace_id):
    try:
        if str(UUID(workspace_id)) != workspace_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as error:
        raise GatewayError("Invalid workspace identity; refusing to write credentials.") from error
    home = root / workspace_id / "home"
    if not home.is_dir():
        return None
    # Workspaces are personal/trusted, but never follow a credential-path symlink.
    for relative in ("", ".config", ".config/ai-gateway", ".config/ai-gateway/key", ".omp", ".omp/agent", ".omp/agent/models.yml", ".omp/agent/models.yaml", ".omp/agent/models.json"):
        if (home / relative).is_symlink():
            raise GatewayError("AI credential/config path is a symlink; refusing to overwrite it.")
    if (root / workspace_id).is_symlink():
        raise GatewayError("Workspace directory is a symlink; refusing to write credentials.")
    return home


def deliver(home, key, url):
    directory = home / ".config/ai-gateway"
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    private_write(directory / "key", key)
    document = {"providers": {"personal-gateway": {
        "baseUrl": url + "/v1", "apiKey": "!cat /home/coder/.config/ai-gateway/key",
        "api": "openai-completions", "discovery": {"type": "openai-models-list"},
    }}}
    # JSON is also valid YAML. Preserve any existing user-authored OMP catalog.
    content = "# Managed by Coder AI gateway provisioning\n" + json.dumps(document, indent=2) + "\n"
    private_write(directory / "models.yml", content)
    models = home / ".omp/agent/models.yml"
    existing = [home / ".omp/agent" / name for name in ("models.yml", "models.yaml", "models.json")]
    if not any(path.exists() for path in existing) or (models.exists() and models.read_text().startswith("# Managed by Coder AI gateway provisioning\n")):
        private_write(models, content)


def sync(coder, gateway, state_path, root, models):
    if not models or any(not isinstance(model, str) or not model.strip() or model == "*" for model in models):
        raise GatewayError("Configure a nonempty list of allowed model aliases; wildcard access is not supported.")
    workspaces = []
    total = None
    while True:
        status, listing = coder.request("GET", f"/api/v2/workspaces?q=owner%3Ame&limit=100&offset={len(workspaces)}")
        if status != 200 or not isinstance(listing, dict) or not isinstance(listing.get("workspaces"), list):
            raise GatewayError("AI provisioning could not list Coder workspaces; no keys were removed.")
        if total is None:
            total = listing.get("count")
        if not isinstance(total, int) or total < 0 or listing.get("count") != total:
            raise GatewayError("Coder workspace listing changed or is incomplete; no keys were removed.")
        page = listing["workspaces"]
        workspaces.extend(page)
        if len(workspaces) == total:
            break
        if len(workspaces) > total or len(page) < 100:
            raise GatewayError("Coder workspace listing is incomplete; no keys were removed.")
    if len({workspace["id"] for workspace in workspaces}) != len(workspaces):
        raise GatewayError("Coder workspace listing contains duplicate identities; no keys were removed.")
    state = json.loads(state_path.read_text()) if state_path.exists() else {"gateway_url": gateway.url, "workspaces": {}}
    if state.get("gateway_url") != gateway.url:
        raise GatewayError("AI gateway URL changed; revoke old managed keys and archive ai-gateway.json before switching gateways.")

    def persist():
        private_write(state_path, json.dumps(state, indent=2))

    current = set()
    for workspace in workspaces:
        workspace_id = workspace["id"]
        current.add(workspace_id)
        home = workspace_home(root, workspace_id)
        if home is None:
            continue
        entry = state["workspaces"].get(workspace_id)
        if entry is None:
            key = "sk-" + secrets.token_hex(32)
            entry = {"key": key, "hash": hashlib.sha256(key.encode()).hexdigest(), "status": "pending"}
            state["workspaces"][workspace_id] = entry
            persist()  # Retry a lost HTTP response with the same key, never mint a duplicate.
        if entry["status"] == "revoked":
            continue
        status, info = gateway.request("GET", "/key/info?key=" + entry["hash"])
        if status == 200:
            if not isinstance(info, dict) or not isinstance(info.get("info"), dict):
                raise GatewayError("AI gateway returned invalid key information.")
            if info["info"].get("status") in ("deleted", "expired"):
                entry["status"] = "revoked"
                persist()
                key_path = home / ".config/ai-gateway/key"
                if key_path.exists() and key_path.read_text() == entry["key"]:
                    key_path.unlink()
                continue
            if info["info"].get("blocked"):
                continue  # An operator's block must not be undone by provisioning.
            if sorted(info["info"].get("models") or []) != sorted(models):
                status, _ = gateway.request("POST", "/key/update", {"key": entry["hash"], "models": models})
                if status != 200:
                    raise GatewayError("AI workspace model permissions could not be updated.")
        elif status == 404:
            if entry["status"] == "active":
                entry["status"] = "revoked"
                persist()  # Manual deletion is respected; never silently issue a replacement.
                key_path = home / ".config/ai-gateway/key"
                if key_path.exists() and key_path.read_text() == entry["key"]:
                    key_path.unlink()
                continue
            status, _ = gateway.request("POST", "/key/generate", {
                "key": entry["key"], "key_alias": "coder-" + workspace_id,
                "models": models, "key_type": "llm_api",
                "metadata": {"managed_by": "coder-dev", "coder_workspace_id": workspace_id},
            })
            if status not in (200, 201):
                raise GatewayError("AI workspace key creation failed; check gateway credentials and model aliases.")
        else:
            raise GatewayError("AI key lookup failed; no replacement key was issued.")
        entry["status"] = "active"
        persist()
        deliver(home, entry["key"], gateway.url)

    for workspace_id in list(state["workspaces"]):
        if workspace_id in current:
            continue
        entry = state["workspaces"][workspace_id]
        status, info = gateway.request("GET", "/key/info?key=" + entry["hash"])
        if status == 200 and isinstance(info, dict) and isinstance(info.get("info"), dict):
            if info["info"].get("status") != "deleted":
                status, _ = gateway.request("POST", "/key/delete", {"keys": [entry["hash"]]})
        elif status != 404:
            raise GatewayError("Deleted workspace key lookup failed; provisioning will retry.")
        if status not in (200, 404):
            raise GatewayError("Deleted workspace key revocation failed; provisioning will retry.")
        home = workspace_home(root, workspace_id)
        if home:
            key_path = home / ".config/ai-gateway/key"
            if key_path.exists() and key_path.read_text() == entry["key"]:
                key_path.unlink()
        del state["workspaces"][workspace_id]
        persist()
