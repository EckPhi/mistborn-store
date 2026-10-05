#!/bin/bash
set -eu
if [ -z "${PASSWORD:-}" ] || [ -z "${CUSTOM_USER:-}" ]; then
    echo 'Refusing to start unauthenticated desktop: set CUSTOM_USER and PASSWORD.' >&2
    exit 1
fi
exec /init "$@"
