#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
    cd "$(
        dirname "${BASH_SOURCE[0]}"
    )/.."
    pwd
)"

TMP="$(
    mktemp -d
)"

cleanup() {
    rm -rf "$TMP"
}

trap cleanup EXIT

OUTPUT="$(
    XDG_CONFIG_HOME="$TMP/config" \
    XDG_DATA_HOME="$TMP/data" \
    XDG_STATE_HOME="$TMP/state" \
    HATIRLATICI_PYTHON="python3" \
    "$ROOT/hatirlatici_app.sh" \
    --selftest
)"

printf '%s\n' "$OUTPUT"

printf '%s\n' "$OUTPUT" |
    grep -Fq \
    'PUBLIC_LAUNCHER_SELFTEST=PASS'

printf '%s\n' "$OUTPUT" |
    grep -Fq \
    'SETUP_COMPLETE=NO'

echo "PUBLIC_LAUNCHER_RUNTIME_REGRESSION=PASS"
