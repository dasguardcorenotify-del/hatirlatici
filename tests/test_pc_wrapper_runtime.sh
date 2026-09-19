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
    env -i \
        HOME="$HOME" \
        PATH="/usr/bin:/bin" \
        XDG_CONFIG_HOME="$TMP/config" \
        XDG_DATA_HOME="$TMP/data" \
        XDG_STATE_HOME="$TMP/state" \
        HATIRLATICI_WRAPPER_SELFTEST="1" \
        HATIRLATICI_PYTHON="python3" \
        "$ROOT/pc_notify.sh"
)"

printf '%s\n' "$OUTPUT"

printf '%s\n' "$OUTPUT" |
    grep -Fq \
    'PC_WRAPPER_SELFTEST=PASS'

printf '%s\n' "$OUTPUT" |
    grep -Fq \
    "DATA_DIR=$TMP/data/hatirlatici"

echo "PC_WRAPPER_XDG_REGRESSION=PASS"
