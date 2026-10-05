#!/usr/bin/env python3
import fcntl, os, subprocess, sys, traceback
from datetime import datetime
from pathlib import Path
from installer import discover, extract

def dialog(*args):
    return subprocess.run(['zenity', *args], text=True, capture_output=True)

def main(action):
    config = Path('/config')
    for name in ('logs', 'installers', 'wine', 'Desktop', 'uploads'):
        (config/name).mkdir(parents=True, exist_ok=True)
    prefix = config/'wine/solid-edge'
    os.environ.update(WINEPREFIX=str(prefix), WINEARCH='win64')
    lock = (config/'wine/.operation.lock').open('w')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise ValueError('Another Wine operation is running. Close it first.')
    with (config/'logs'/f'{action}-{datetime.now():%Y%m%d-%H%M%S}.log').open('w') as log:
        def run(args, **kw):
            log.write('Command: ' + repr(args) + '\n'); log.flush()
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True, **kw)
        if action == 'install':
            choice = dialog('--list', '--title=Choose installer source', '--column=Source', 'Archive', 'Host folder')
            if choice.returncode: return
            args = ['--file-selection', '--title=Select complete installer archive or folder', '--filename=/config/uploads/']
            if choice.stdout.strip() == 'Host folder': args.append('--directory')
            selected = dialog(*args)
            if selected.returncode: return
            source = Path(selected.stdout.strip())
            setup = discover(source) if source.is_dir() else extract(source, config/'installers')
            log.write('Validated installer: ' + str(setup) + '\n'); log.flush()
            confirm = dialog('--question', '--title=Start graphical Solid Edge installer?', '--text=This starts Siemens setup in Wine. Review all terms and installation options yourself. Compatibility with 2026 (2510) is experimental. Continue?')
            if confirm.returncode: return
            run(['wineboot', '-u'])
            # Equivalent Windows 11 prefix setting to the reference winetricks win11 verb.
            run(['winecfg', '-v', 'win11'])
            run(['wine', str(setup)], cwd=setup.parent)
            run(['wineserver', '-w'])
            dialog('--info', '--text=Installer process finished. This does not prove installation succeeded. Review installer messages and logs, then try Launch Solid Edge.')
        elif action == 'launch':
            if not prefix.exists(): raise ValueError('Wine prefix missing. Use Install Solid Edge with your complete Siemens installer first.')
            candidates = [p for p in (prefix/'drive_c/Program Files').glob('Siemens/**/Edge.exe') if p.is_file()]
            if len(candidates) != 1: raise ValueError('Solid Edge executable missing or ambiguous. Check installation and /config/logs. Expected one Siemens Edge.exe under Program Files.')
            run(['wine', str(candidates[0])], cwd=candidates[0].parent)
            run(['wineserver', '-w'])
        elif action == 'logs':
            subprocess.run(['thunar', '/config/logs'], check=True)
        else: raise ValueError('Unknown action')

if __name__ == '__main__':
    try: main(sys.argv[1])
    except Exception as e:
        traceback.print_exc()
        dialog('--error', '--text=' + str(e) + '\nLogs: /config/logs')
        sys.exit(1)
