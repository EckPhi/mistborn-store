#!/bin/bash
set -euo pipefail
[[ "$WORKSPACE_ID" =~ ^[a-zA-Z0-9-]+$ ]] || exit 1
root="/persistent/$WORKSPACE_ID"
mkdir -p "$root" "/cache-storage/$WORKSPACE_ID"
if [ ! -f "$root/.bind-migration-complete" ]; then
  for kind in home source; do
    destination="$root/$kind"
    if [ ! -f "$root/.$kind-migration-complete" ]; then
      if [ -e "$destination" ] || [ -L "$destination" ]; then
        echo "Migration refused: $destination exists without a completion marker; inspect it before retrying." >&2
        exit 1
      fi
      staging="$root/.$kind-migration"
      rm -rf "$staging"
      mkdir -p "$staging"
      if [ -d "/legacy/workspaces/$WORKSPACE_ID/$kind" ]; then
        cp -a "/legacy/workspaces/$WORKSPACE_ID/$kind/." "$staging/"
      fi
      mv "$staging" "$destination"
      touch "$root/.$kind-migration-complete"
    fi
  done
  touch "$root/.bind-migration-complete"
fi
chown 1000:1000 "$root/home" "$root/source" "/cache-storage/$WORKSPACE_ID"
