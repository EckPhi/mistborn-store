#!/usr/bin/env python3
"""Private installer preparation. Never executes archive content."""
import argparse, os, shutil, stat, tarfile, tempfile, zipfile
from pathlib import Path, PurePosixPath
MAX_BYTES = 30 * 1024**3
MAX_FILES = 100000

def safe_name(name):
    name = name.replace("\\", "/")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or any(":" in x for x in p.parts) or "\x00" in name:
        raise ValueError("Unsafe archive path: " + repr(name))
    return p

def discover(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Installer root must not be a symbolic link")
    matches = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(directory)/d).is_symlink()]
        p = Path(directory)
        names = {x.name.casefold(): x for x in p.iterdir()}
        if 'setup.exe' not in names:
            continue
        required = ['setup.exe', 'setup.ini', 'siemens solid edge 2026.msi', 'issetupprerequisites', 'licensefile']
        if all(x in names for x in required) and any(x.endswith('.cab') for x in names):
            lic = names['licensefile']/ 'SELicense.lic'
            if names['issetupprerequisites'].is_dir() and lic.is_file() and all(names[x].is_file() for x in required[:3]):
                # Reject symlinks anywhere in the candidate tree.
                if any(x.is_symlink() for x in p.rglob('*')):
                    raise ValueError('Installer contains symbolic links')
                matches.append(names['setup.exe'])
    if len(matches) != 1:
        raise ValueError(f'Expected one complete 2026 installer; found {len(matches)}. Preserve setup.exe, Setup.ini, MSI, all CABs, ISSetupPrerequisites and LicenseFile/SELicense.lic. Select a narrower folder if multiple installers exist.')
    return matches[0]

def extract(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.extract-', dir=destination))
    total = 0
    seen = set()
    try:
        archive = zipfile.ZipFile(source) if zipfile.is_zipfile(source) else tarfile.open(source, 'r:*')
        with archive:
            members = archive.infolist() if isinstance(archive, zipfile.ZipFile) else archive.getmembers()
            if len(members) > MAX_FILES: raise ValueError('Too many archive entries')
            for member in members:
                iszip = isinstance(archive, zipfile.ZipFile)
                name = member.filename if iszip else member.name
                rel = safe_name(name)
                key = str(rel).casefold()
                if key in seen: raise ValueError('Duplicate archive path')
                seen.add(key)
                mode = member.external_attr >> 16 if iszip else member.mode
                if (iszip and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or (not iszip and not (member.isfile() or member.isdir())):
                    raise ValueError('Links and special files are forbidden')
                size = member.file_size if iszip else member.size
                total += size
                if total > MAX_BYTES: raise ValueError('Archive exceeds 30 GiB extraction limit')
                if shutil.disk_usage(stage).free < size + 1024**3: raise ValueError('Insufficient free disk space')
                target = stage.joinpath(*rel.parts)
                if member.is_dir() if iszip else member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with (archive.open(member) if iszip else archive.extractfile(member)) as src, target.open('xb') as dst:
                        shutil.copyfileobj(src, dst, 1024*1024)
                    target.chmod(0o600)
        setup = discover(stage)
        result = destination / ('prepared-' + stage.name.removeprefix('.extract-'))
        relative = setup.relative_to(stage)
        stage.rename(result)
        return result / relative
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--destination', type=Path, default=Path('/config/installers'))
    args = parser.parse_args()
    try:
        print(discover(args.source) if args.source.is_dir() else extract(args.source, args.destination))
    except (ValueError, OSError, tarfile.TarError, zipfile.BadZipFile) as e:
        parser.exit(1, str(e) + '\n')
