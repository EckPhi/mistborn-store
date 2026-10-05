"""Experimental operator bridge: create a Coder workspace and connect an Omnigent host.

Not a native Omnigent provider. Requires matching authenticated Coder CLI;
connecting requests workspace-side Omnigent login interactively. Never deletes data.
"""
import argparse
import os
import re
import shlex
import subprocess


def commands(name, url):
    if not re.fullmatch(r'agent-[a-z0-9][a-z0-9-]{0,25}', name):
        raise ValueError('Use a unique agent- prefixed workspace name, at most 32 characters')
    if not url.startswith(('http://', 'https://')):
        raise ValueError('Omnigent requires an HTTP(S) URL')
    create = ['coder', 'create', name, '--template', 'general-development',
              '--yes', '--use-parameter-defaults', '--stop-after', '8h',
              '--parameter', 'docker_development=true',
              '--parameter', 'ai_agents=true']
    # Host stays in the foreground. Disconnect/restart handling is upstream's job.
    runner = ['coder', 'ssh', name, '--', 'bash', '-lc',
              shlex.quote('exec omnigent host --server ' + shlex.quote(url) + ' --no-open')]
    return create, runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('--omnigent-url', required=True)
    parser.add_argument('--connect', action='store_true', help='Log in interactively in the new workspace and connect its host')
    args = parser.parse_args()
    create, runner = commands(args.name, args.omnigent_url)
    env = dict(os.environ)
    if env.get('CODER_API_TOKEN'):
        env['CODER_SESSION_TOKEN'] = env.pop('CODER_API_TOKEN')
    result = subprocess.run(create, env=env, capture_output=True, timeout=3600)
    if result.returncode:
        raise SystemExit('Workspace creation failed; check name collisions, authorization and build status privately.')
    print('Workspace created. Authenticate Omnigent inside it before connecting the host.')
    if args.connect:
        login = ['coder', 'ssh', '--tty', args.name, '--', 'omnigent', 'login', shlex.quote(args.omnigent_url)]
        if subprocess.run(login, env=env).returncode:
            raise SystemExit('Omnigent login failed; workspace retained.')
        result = subprocess.run(runner, env=env)
        if result.returncode:
            raise SystemExit('Runner exited unsuccessfully; workspace is retained for diagnosis.')
    print('Workspace retained. Stop it with Coder when finished; source deletion requires a separate decision.')


if __name__ == '__main__':
    main()
