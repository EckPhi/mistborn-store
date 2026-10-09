"""Filesystem checks for browseable workspace snapshots."""
import importlib.util
import json
from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("snapshot", Path(__file__).resolve().parents[2] / "apps/coder-dev/bootstrap/snapshot.py")
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.live = self.root / "live"
        self.home = self.live / "workspace-1/home"
        self.source = self.live / "workspace-1/source"
        self.home.mkdir(parents=True)
        self.source.mkdir()
        self.backups = self.root / "snapshots"

    def git(self, repository, *arguments):
        subprocess.run(["git", "-C", str(repository), *arguments], check=True,
                       capture_output=True)

    def test_git_ignores_preserve_tracked_and_nonignored_files(self):
        repo = self.source / "project"
        repo.mkdir()
        self.git(repo, "init")
        (repo / ".gitignore").write_text("*.secret\nbuild/\n.cache/\n!keep.secret\n")
        (repo / "tracked.secret").write_text("tracked modified content")
        self.git(repo, "add", "-f", "tracked.secret")
        (repo / "hidden.secret").write_text("omit")
        (repo / "keep.secret").write_text("keep")
        (repo / "new file\nwith newline.txt").write_text("uncommitted")
        (repo / "build").mkdir()
        (repo / "build/output").write_text("omit")
        (repo / ".cache").mkdir()
        (repo / ".cache/tracked").write_text("tracked cache-named source")
        self.git(repo, "add", "-f", ".cache/tracked")
        (repo / ".git/info/exclude").write_text("local.tmp\n")
        (repo / "local.tmp").write_text("omit")
        nested = repo / "nested"
        nested.mkdir()
        (nested / ".gitignore").write_text("*.tmp\n")
        (nested / "generated.tmp").write_text("omit")
        tree = self.create() / "workspaces/workspace-1/source/project"
        for name in ("tracked.secret", "keep.secret", "new file\nwith newline.txt", ".cache/tracked", ".git/index"):
            self.assertTrue((tree / name).exists(), name)
        for name in ("hidden.secret", "build", "local.tmp", "nested/generated.tmp"):
            self.assertFalse((tree / name).exists(), name)

    def test_nested_repository_has_its_own_ignore_rules(self):
        self.git(self.source, "init")
        nested = self.source / "nested"
        nested.mkdir()
        self.git(nested, "init")
        (nested / ".gitignore").write_text("generated\n")
        (nested / "generated").write_text("omit")
        (nested / "source").write_text("keep")
        tree = self.create() / "workspaces/workspace-1/source/nested"
        self.assertFalse((tree / "generated").exists())
        self.assertTrue((tree / "source").exists())

    def test_git_failure_keeps_previous_snapshot(self):
        self.git(self.source, "init")
        first = self.create()
        with patch.object(snapshot, "_git_ignored", side_effect=OSError("git unavailable")):
            with self.assertRaises(OSError):
                self.create()
        self.assertEqual(json.loads((self.backups / "latest.json").read_text())["directory"], first.name)
        self.assertFalse(json.loads((self.backups / "status.json").read_text())["ok"])

    def test_interrupted_attempt_does_not_report_previous_success(self):
        completed = self.create()
        with patch.object(snapshot, "_create", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.create()
        status = json.loads((self.backups / "status.json").read_text())
        self.assertFalse(status["ok"])
        self.assertEqual(status["state"], "in_progress")
        self.assertEqual(json.loads((self.backups / "latest.json").read_text())["directory"], completed.name)
        self.assertTrue(completed.exists())

    def create(self, **kwargs):
        return snapshot.create_snapshot(self.live, self.backups, **kwargs)

    def test_filter_and_preserve_broken_links(self):
        (self.home / ".cache").mkdir()
        (self.home / ".cache/build").write_text("disposable")
        (self.source / "build").mkdir()
        (self.source / "build/artifact").write_text("keep")
        (self.source / "broken").symlink_to("/missing/cache/artifact")
        runtime = self.home / "runtime.sock"
        runtime.touch()
        original_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            info = original_lstat(path, *args, **kwargs)
            if path == runtime:
                return os.stat_result((stat.S_IFSOCK | 0o600,) + tuple(info)[1:])
            return info
        self.patch = patch.object(Path, "lstat", lstat)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        result = self.create(workspace_metadata=[{"id": "workspace-1", "name": "dev", "owner_name": "alice"}])
        tree = result / "workspaces/workspace-1"
        self.assertFalse((tree / "home/.cache").exists())
        self.assertFalse((tree / "home/runtime.sock").exists())
        self.assertEqual((tree / "source/build/artifact").read_text(), "keep")
        self.assertEqual((tree / "source/broken").readlink(), Path("/missing/cache/artifact"))
        manifest = json.loads((result / "manifest.json").read_text())
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["workspaces"][0]["name"], "dev")
        self.assertTrue(manifest["completed_at"].endswith("+00:00"))

    def test_incremental_link_and_changed_bytes_with_same_mtime(self):
        file = self.source / "code"
        file.write_text("one")
        first = self.create()
        second = self.create()
        relative = "workspaces/workspace-1/source/code"
        self.assertEqual((first / relative).stat().st_ino, (second / relative).stat().st_ino)
        import os
        info = file.stat()
        file.write_text("two")
        os.utime(file, ns=(info.st_atime_ns, info.st_mtime_ns))
        third = self.create()
        self.assertNotEqual((second / relative).stat().st_ino, (third / relative).stat().st_ino)
        self.assertEqual((first / relative).read_text(), "one")
        self.assertEqual((third / relative).read_text(), "two")

    def test_failure_keeps_latest_and_cleans_staging(self):
        (self.source / "code").write_text("one")
        first = self.create()
        with patch.object(snapshot, "_copy", side_effect=OSError("copy failed")):
            with self.assertRaisesRegex(OSError, "copy failed"):
                self.create()
        self.assertEqual(json.loads((self.backups / "latest.json").read_text())["directory"], first.name)
        self.assertFalse(json.loads((self.backups / "status.json").read_text())["ok"])
        self.assertEqual(snapshot._completed(self.backups), [first])
        self.assertEqual(list(self.backups.glob(".incomplete-*")), [])

    def test_retention_only_removes_completed_snapshots(self):
        (self.source / "code").write_text("one")
        self.backups.mkdir()
        unrelated = self.backups / "2020-01-01T000000.000000Z"
        unrelated.mkdir()
        results = [self.create() for _ in range(5)]
        self.assertEqual(snapshot._completed(self.backups), results[-3:])
        self.assertTrue(unrelated.exists())
        self.assertEqual(json.loads((self.backups / "latest.json").read_text())["directory"], results[-1].name)

    def test_deleted_files_remain_only_in_previous_snapshot(self):
        file = self.source / "removed"
        file.write_text("recover me")
        first = self.create()
        file.unlink()
        second = self.create()
        self.assertTrue((first / "workspaces/workspace-1/source/removed").exists())
        self.assertFalse((second / "workspaces/workspace-1/source/removed").exists())

    def test_changed_permissions_do_not_modify_previous_inode(self):
        file = self.source / "script"
        file.write_text("script")
        file.chmod(0o600)
        first = self.create()
        file.chmod(0o700)
        second = self.create()
        relative = "workspaces/workspace-1/source/script"
        self.assertEqual(stat.S_IMODE((first / relative).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((second / relative).stat().st_mode), 0o700)
        self.assertNotEqual((first / relative).stat().st_ino, (second / relative).stat().st_ino)

    def test_missing_storage_never_publishes_empty_success(self):
        with self.assertRaises(ValueError):
            snapshot.create_snapshot(self.root / "missing", self.backups)
        self.assertEqual(snapshot._completed(self.backups), [])
        self.assertFalse(json.loads((self.backups / "status.json").read_text())["ok"])

    def test_explicit_volume_mount_mapping(self):
        result = self.create(workspace_paths={"named-volume": {"home": self.home, "source": self.source}})
        self.assertTrue((result / "workspaces/named-volume/home").is_dir())


if __name__ == "__main__":
    unittest.main()
