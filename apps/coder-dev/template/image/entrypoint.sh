#!/bin/bash
set -euo pipefail
if [ ! -e /home/coder/.coder-home-initialized ]; then
  cp -an /etc/skel/. /home/coder/
  chown -R coder:coder /home/coder
  touch /home/coder/.coder-home-initialized
  chown coder:coder /home/coder/.coder-home-initialized
fi
mkdir -p /cache/{ccache,conan,pip,uv,npm,pnpm} /workspaces /home/coder/.ssh /home/coder/.config /home/coder/.local
chown coder:coder /home/coder /home/coder/.ssh /home/coder/.config /home/coder/.local /workspaces /cache /cache/*
chmod 700 /home/coder/.ssh
if [ -S /var/run/docker.sock ]; then
  gid=$(stat -c '%g' /var/run/docker.sock)
  group=$(getent group "$gid" | cut -d: -f1 || true)
  if [ -z "$group" ]; then group=coder-host-docker-$gid; groupadd -g "$gid" "$group"; fi
  usermod -aG "$group" coder
fi
exec gosu coder "$@"
