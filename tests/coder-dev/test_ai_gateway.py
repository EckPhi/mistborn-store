import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ai_gateway", ROOT / "apps/coder-dev/bootstrap/ai_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class Coder:
    def __init__(self, workspace_id):
        self.workspaces = [{"id": workspace_id, "name": "dev"}]
        self.incomplete = False
        self.offline = False

    def request(self, method, path, body=None):
        if self.offline:
            return 503, None
        offset = int(parse_qs(urlsplit(path).query).get("offset", [0])[0])
        return 200, {"workspaces": self.workspaces[offset:offset + 100], "count": len(self.workspaces) + int(self.incomplete)}


class LiteLLM:
    url = "https://ai.example.test"

    def __init__(self):
        self.keys = {}
        self.created = 0
        self.lost_response = False
        self.unavailable = False

    def request(self, method, path, body=None):
        if self.unavailable:
            return 503, None
        if path.startswith("/key/info?"):
            key_hash = path.split("=", 1)[1]
            return (200, {"info": self.keys[key_hash]}) if key_hash in self.keys else (404, None)
        if path == "/key/generate":
            self.created += 1
            key_hash = hashlib.sha256(body["key"].encode()).hexdigest()
            self.keys[key_hash] = {"models": body["models"], "key_type": body["key_type"], "status": "active"}
            if self.lost_response:
                self.lost_response = False
                raise gateway.GatewayError("Response lost")
            return 200, body
        if path == "/key/update":
            self.keys[body["key"]]["models"] = body["models"]
            return 200, {}
        if path == "/key/delete":
            for key_hash in body["keys"]:
                self.keys.pop(key_hash, None)
            return 200, {}
        raise AssertionError(path)


class ProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace_id = str(uuid4())
        self.home = self.root / self.workspace_id / "home"
        self.home.mkdir(parents=True)
        self.state = self.root / "state/ai-gateway.json"
        self.coder = Coder(self.workspace_id)
        self.api = LiteLLM()

    def sync(self, models=None):
        gateway.sync(self.coder, self.api, self.state, self.root, ["coding"] if models is None else models)

    def test_restarts_reuse_keys_and_deliver_only_llm_key(self):
        self.sync()
        key = (self.home / ".config/ai-gateway/key").read_text()
        self.sync()
        self.assertEqual(self.api.created, 1)
        self.assertEqual(key, (self.home / ".config/ai-gateway/key").read_text())
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.home / ".config/ai-gateway/key").stat().st_mode & 0o777, 0o600)
        self.assertEqual(next(iter(self.api.keys.values()))["key_type"], "llm_api")
        config = (self.home / ".omp/agent/models.yml").read_text()
        self.assertIn("https://ai.example.test/v1", config)
        self.assertNotIn(key, config)

    def test_lost_creation_response_recovers_without_duplicate(self):
        self.api.lost_response = True
        with self.assertRaises(gateway.GatewayError):
            self.sync()
        self.sync()
        self.assertEqual(self.api.created, 1)
        self.assertTrue((self.home / ".config/ai-gateway/key").exists())

    def test_deleted_workspace_is_revoked_but_partial_listing_is_safe(self):
        self.sync()
        self.coder.workspaces = []
        self.coder.incomplete = True
        with self.assertRaises(gateway.GatewayError):
            self.sync()
        self.assertEqual(len(self.api.keys), 1)
        self.coder.incomplete = False
        self.sync()
        self.assertFalse(self.api.keys)
        self.assertFalse((self.home / ".config/ai-gateway/key").exists())

    def test_operator_revocation_is_not_undone(self):
        self.sync()
        next(iter(self.api.keys.values()))["status"] = "deleted"
        self.sync()
        self.sync()
        self.assertEqual(self.api.created, 1)
        self.assertFalse((self.home / ".config/ai-gateway/key").exists())

    def test_operator_block_and_user_config_are_preserved(self):
        models = self.home / ".omp/agent/models.yml"
        models.parent.mkdir(parents=True)
        models.write_text("providers: {existing: {auth: none}}\n")
        self.sync()
        next(iter(self.api.keys.values()))["blocked"] = True
        self.sync(["fast"])
        self.assertEqual(next(iter(self.api.keys.values()))["models"], ["coding"])
        self.assertEqual(models.read_text(), "providers: {existing: {auth: none}}\n")
        self.assertTrue((self.home / ".config/ai-gateway/models.yml").exists())

    def test_scope_changes_update_existing_key(self):
        self.sync()
        self.sync(["fast"])
        self.assertEqual(self.api.created, 1)
        self.assertEqual(next(iter(self.api.keys.values()))["models"], ["fast"])

    def test_outage_does_not_revoke_or_replace_keys(self):
        self.sync()
        self.api.unavailable = True
        with self.assertRaises(gateway.GatewayError):
            self.sync()
        self.assertEqual(self.api.created, 1)
        self.assertEqual(len(self.api.keys), 1)

    def test_symlinks_and_invalid_ids_cannot_redirect_secret_writes(self):
        (self.home / ".config").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(gateway.GatewayError):
            self.sync()
        self.assertEqual(self.api.created, 0)
        self.coder.workspaces = [{"id": "../../escape"}]
        with self.assertRaises(gateway.GatewayError):
            self.sync()

    def test_empty_or_unrestricted_permissions_are_rejected(self):
        for models in ([], ["*"], [""]):
            with self.assertRaises(gateway.GatewayError):
                self.sync(models)
        self.assertEqual(self.api.created, 0)

    def test_gateway_switch_requires_explicit_cleanup(self):
        self.sync()
        self.api.url = "https://other.example.test"
        with self.assertRaises(gateway.GatewayError):
            self.sync()
        self.assertEqual(self.api.created, 1)

    def test_all_pages_are_read_before_deleting_managed_keys(self):
        self.sync()
        self.coder.workspaces = [{"id": str(uuid4())} for _ in range(100)] + [{"id": self.workspace_id}]
        self.sync()
        self.assertEqual(self.api.created, 1)
        self.assertTrue((self.home / ".config/ai-gateway/key").exists())

    def test_admin_gateway_key_is_not_inherited_by_coder_cli(self):
        spec = importlib.util.spec_from_file_location("bootstrap_gateway_test", ROOT / "apps/coder-dev/bootstrap/bootstrap.py")
        bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bootstrap)
        from types import SimpleNamespace
        with patch.dict(os.environ, {"CODER_DEV_AI_GATEWAY_ADMIN_KEY": "secret-admin"}), patch.object(bootstrap.subprocess, "run") as run:
            bootstrap.cli(SimpleNamespace(url="http://coder.test", token="session"), "list")
        self.assertNotIn("CODER_DEV_AI_GATEWAY_ADMIN_KEY", run.call_args.kwargs["env"])


if __name__ == "__main__":
    unittest.main()
