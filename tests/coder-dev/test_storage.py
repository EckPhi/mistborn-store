"""Exercise the migration command without a Docker daemon."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "apps/coder-dev/template/storage-migrate.sh"


class StorageMigrationTests(unittest.TestCase):
    def test_unmarked_destination_fails_without_overwriting_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "persistent/test-id/home"
            home.mkdir(parents=True)
            (home / "important").write_text("keep me")
            script = SCRIPT.read_text()
            for original, destination in (("/persistent", root / "persistent"),
                                          ("/cache-storage", root / "cache-storage"),
                                          ("/legacy", root / "legacy")):
                script = script.replace(original, str(destination))
            result = subprocess.run(["bash", "-ec", script],
                                    env=dict(os.environ, WORKSPACE_ID="test-id"),
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exists without a completion marker", result.stderr)
            self.assertEqual((home / "important").read_text(), "keep me")
            self.assertFalse((home.parent / ".bind-migration-complete").exists())

    def test_migration_preserves_originals_links_and_current_named_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy/workspaces/test-id"
            (legacy / "home").mkdir(parents=True)
            (legacy / "source").mkdir()
            (legacy / "home/settings").write_text("original")
            (legacy / "source/main.py").write_text("print('hello')")
            (legacy / "home/broken").symlink_to("missing")
            script = SCRIPT.read_text()
            for original, destination in (("/persistent", root / "persistent"),
                                          ("/cache-storage", root / "cache-storage"),
                                          ("/legacy", root / "legacy")):
                script = script.replace(original, str(destination))
            # Ownership requires root only in production, and is unrelated to copying.
            script = script.replace("chown 1000:1000", "true")
            environment = dict(os.environ, WORKSPACE_ID="test-id")
            def run():
                result = subprocess.run(["bash", "-ec", script], env=environment,
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            run()
            destination = root / "persistent/test-id"
            self.assertEqual((destination / "home/settings").read_text(), "original")
            self.assertTrue((destination / "home/broken").is_symlink())
            self.assertEqual(os.readlink(destination / "home/broken"), "missing")
            self.assertEqual((destination / "source/main.py").read_text(), "print('hello')")
            self.assertTrue((legacy / "home/settings").exists())
            self.assertEqual(list((root / "cache-storage/test-id").iterdir()), [])
            (destination / "home/settings").write_text("new version")
            run()
            self.assertEqual((destination / "home/settings").read_text(), "new version")


if __name__ == "__main__":
    unittest.main()
