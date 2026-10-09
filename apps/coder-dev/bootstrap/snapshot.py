"""Dated, filtered file snapshots; callers must stop workspace writers first."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

# Package caches are disposable; build outputs and application data are retained.
CACHE_NAMES = {".cache", "__pycache__", ".npm", ".yarn-cache", ".pnpm-store", ".uv-cache"}
SNAPSHOT_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6}\.\d{6}Z$")


def _digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


def _git_ignored(repository):
    """Ask Git for ignored untracked paths; never run repository helpers."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={repository}", "-c", "core.fsmonitor=false",
             "-c", "core.excludesFile=/dev/null", "-C", str(repository), "ls-files",
             "--others", "--ignored", "--exclude-standard", "--directory", "-z"],
            env=environment, capture_output=True, timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise OSError(f"Git ignore evaluation timed out: {repository}") from error
    if result.returncode:
        raise OSError(f"Git ignore evaluation failed: {repository}")
    return {repository / os.fsdecode(value).rstrip("/") for value in result.stdout.split(b"\0") if value}


def _copy(source, destination, previous=None, ignored=None, git_metadata=False):
    info = source.lstat()
    if stat.S_ISLNK(info.st_mode):
        destination.symlink_to(os.readlink(source))
    elif stat.S_ISDIR(info.st_mode):
        if not git_metadata and (source / ".git").exists():
            ignored = _git_ignored(source)
        destination.mkdir()
        if previous is not None and (previous.is_symlink() or not previous.is_dir()):
            previous = None
        for child in source.iterdir():
            if (git_metadata or ignored is not None or child.name not in CACHE_NAMES) and (ignored is None or child not in ignored):
                _copy(child, destination / child.name, previous / child.name if previous is not None else None,
                      ignored, git_metadata or child.name == ".git")
        shutil.copystat(source, destination, follow_symlinks=False)
    elif stat.S_ISREG(info.st_mode):
        # Compare bytes, not just timestamps: tools can preserve mtimes on edits.
        old_info = previous.lstat() if previous is not None and previous.exists() else None
        if (old_info is not None and stat.S_ISREG(old_info.st_mode)
                and info.st_size == old_info.st_size
                and info.st_mtime_ns == old_info.st_mtime_ns
                and stat.S_IMODE(info.st_mode) == stat.S_IMODE(old_info.st_mode)
                and _digest(source) == _digest(previous)):
            os.link(previous, destination)
        else:
            shutil.copy2(source, destination, follow_symlinks=False)
    # Sockets, FIFOs and device nodes are runtime state, never copied.


def _completed(root):
    result = []
    for path in root.iterdir():
        if path.is_symlink() or not path.is_dir() or not SNAPSHOT_NAME.fullmatch(path.name):
            continue
        try:
            manifest = json.loads((path / "manifest.json").read_text())
            if manifest.get("complete") is True and manifest.get("format_version") == 1:
                result.append(path)
        except (OSError, ValueError):
            continue
    return sorted(result, key=lambda path: path.name)


def create_snapshot(workspaces_root, snapshots_root, workspace_metadata=None, retain=3,
                    workspace_paths=None):
    """Snapshot UUID/home,source trees or explicitly mapped named-volume mounts.

    Existing snapshots are immutable: edit a copy, because unchanged regular
    files may share inodes. A failed copy leaves the last completed snapshot.
    """
    if retain < 1:
        raise ValueError("retain must be at least 1")
    root = Path(snapshots_root)
    root.mkdir(parents=True, exist_ok=True)
    # Serialize lifecycle/manual invocations; lock file contains no live data.
    with (root / ".snapshot.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mark_in_progress(root)
        try:
            live = Path(workspaces_root)
            if workspace_paths is None and (not live.is_dir() or live.is_symlink()):
                raise ValueError("Workspace storage root is missing or not a real directory")
            if root.resolve().is_relative_to(live.resolve()):
                raise ValueError("Snapshots must be outside the live workspace tree")
            published = _create(live, root, workspace_metadata or [], retain, workspace_paths)
            _write_json(root / "status.json", {"ok": True, "directory": published.name,
                                              "checked_at": datetime.now(timezone.utc).isoformat()})
            return published
        except (OSError, ValueError) as error:
            _write_json(root / "status.json", {"ok": False, "error": str(error),
                                              "checked_at": datetime.now(timezone.utc).isoformat()})
            raise


def _write_json(path, value):
    temporary = path.with_name("." + path.name + ".next")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def _create(workspaces_root, root, metadata, retain, workspace_paths):
    completed = _completed(root)
    previous = completed[-1] if completed else None
    if workspace_paths is None:
        workspace_paths = {}
        if workspaces_root.exists():
            for workspace in workspaces_root.iterdir():
                if workspace.is_dir() and not workspace.is_symlink():
                    workspace_paths[workspace.name] = {kind: workspace / kind for kind in ("home", "source")}
    by_id = {item["id"]: item for item in metadata}
    staging = Path(tempfile.mkdtemp(prefix=".incomplete-", dir=root))
    try:
        (staging / "workspaces").mkdir()
        records = []
        for workspace_id, paths in sorted(workspace_paths.items()):
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", workspace_id):
                raise ValueError("Unsafe workspace ID")
            target = staging / "workspaces" / workspace_id
            target.mkdir()
            copied = []
            for kind in ("home", "source"):
                source = Path(paths[kind]) if kind in paths else None
                if source is not None and source.exists():
                    if source.is_symlink() or not source.is_dir():
                        raise ValueError("Workspace storage root must be a real directory")
                    old = previous / "workspaces" / workspace_id / kind if previous else None
                    _copy(source, target / kind, old)
                    copied.append(kind)
            record = by_id.get(workspace_id, {})
            records.append({"id": workspace_id, "name": record.get("name"),
                            "owner": record.get("owner_name") or (record.get("owner") or {}).get("username"), "directories": copied})
        completed_at = datetime.now(timezone.utc)
        name = completed_at.strftime("%Y-%m-%dT%H%M%S.%fZ")
        manifest = {"format_version": 1, "complete": True,
                    "completed_at": completed_at.isoformat(), "workspaces": records,
                    "excluded_directory_names": sorted(CACHE_NAMES),
                    "git_ignore": "untracked files ignored by repository .gitignore and .git/info/exclude"}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        published = root / name
        staging.rename(published)
        _write_json(root / "latest.json", {"directory": name, "completed_at": completed_at.isoformat()})
        for expired in (completed + [published])[:-retain]:
            # Source modes can make directories unwritable; restore write access
            # only on directories, never chmod shared regular-file inodes.
            for directory, _, _ in os.walk(expired):
                os.chmod(directory, os.stat(directory).st_mode | stat.S_IWUSR)
            shutil.rmtree(expired)
        return published
    finally:
        if staging.exists():
            for directory, _, _ in os.walk(staging):
                os.chmod(directory, os.stat(directory).st_mode | stat.S_IWUSR)
            shutil.rmtree(staging)


def record_failure(snapshots_root, message):
    """Mark a failed shutdown even when snapshot copying never started."""
    root = Path(snapshots_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "status.json", {"ok": False, "error": message,
                                      "checked_at": datetime.now(timezone.utc).isoformat()})


def mark_in_progress(snapshots_root):
    """A killed helper must not leave the previous attempt reporting success."""
    root = Path(snapshots_root)
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "status.json", {"ok": False, "state": "in_progress",
                                      "started_at": datetime.now(timezone.utc).isoformat()})
