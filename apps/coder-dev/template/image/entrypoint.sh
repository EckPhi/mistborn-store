#!/bin/bash
set -euo pipefail
if [ ! -e /home/coder/.coder-home-initialized ]; then
  cp -an /etc/skel/. /home/coder/
  chown -R coder:coder /home/coder
  touch /home/coder/.coder-home-initialized
  chown coder:coder /home/coder/.coder-home-initialized
fi
if [ ! -e /home/coder/.zshrc ]; then cp /etc/skel/.zshrc /home/coder/.zshrc; chown coder:coder /home/coder/.zshrc; fi
if [ ! -e /home/coder/workspaces ]; then ln -s /workspaces /home/coder/workspaces; chown -h coder:coder /home/coder/workspaces; fi
mkdir -p /cache/{ccache,conan,pip,uv,uv-python,npm,pnpm,pub,cargo-target,playwright} /workspaces /home/coder/.ssh /home/coder/.config /home/coder/.local /home/coder/.cargo
chown coder:coder /home/coder /home/coder/.ssh /home/coder/.config /home/coder/.local /home/coder/.cargo /workspaces /cache /cache/*
chmod 700 /home/coder/.ssh
exec gosu coder "$@"
