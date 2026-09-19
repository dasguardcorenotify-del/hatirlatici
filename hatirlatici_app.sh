#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
    cd -- "$(
        dirname -- "${BASH_SOURCE[0]}"
    )"
    pwd
)"

PYTHON_BIN="${HATIRLATICI_PYTHON:-python3}"

exec "$PYTHON_BIN" \
    "$ROOT/public_launcher.py" \
    "$@"
