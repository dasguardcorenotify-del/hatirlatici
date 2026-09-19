#!/usr/bin/env bash
set -euo pipefail

PYVER="$(
    /usr/bin/python3 -c \
        'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
)"

APP_ROOT="/app/lib/hatirlatici"

SITE_PACKAGES="/app/lib/python${PYVER}/site-packages"

# Do not inherit a caller-controlled module path or per-user site packages.
# The public Flatpak executes only the reviewed modules installed below /app.
export PYTHONPATH="$APP_ROOT:$APP_ROOT/ui_v2:$SITE_PACKAGES"
export PYTHONNOUSERSITE=1

exec /usr/bin/python3 \
    "$APP_ROOT/public_launcher.py" \
    "$@"
