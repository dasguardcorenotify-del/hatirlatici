#!/usr/bin/env bash
set -euo pipefail

ROOT="$(
    cd -- "$(
        dirname -- "${BASH_SOURCE[0]}"
    )"
    pwd
)"

PYTHON_BIN="${HATIRLATICI_PYTHON:-python3}"

"$PYTHON_BIN" \
    "$ROOT/runtime_config.py" \
    --ensure \
    >/dev/null

DATA_DIR="$(
    "$PYTHON_BIN" \
        "$ROOT/runtime_config.py" \
        --data-dir
)"

CSV="$DATA_DIR/pc_hatirlatmalar.csv"

if [[ "${HATIRLATICI_WRAPPER_SELFTEST:-0}" == "1" ]]; then
    [[ -f "$ROOT/pc_notify.py" ]] || {
        echo "SELFTEST_FAIL=pc_notify.py"
        exit 42
    }

    [[ -f "$ROOT/ui_v2/integrity.py" ]] || {
        echo "SELFTEST_FAIL=integrity.py"
        exit 43
    }

    echo "PC_WRAPPER_SELFTEST=PASS"
    echo "CODE_ROOT=$ROOT"
    echo "DATA_DIR=$DATA_DIR"

    exit 0
fi

if [[ -f "$CSV" ]]; then
    "$PYTHON_BIN" \
        "$ROOT/ui_v2/integrity.py" \
        pc \
        "$CSV"
fi

exec "$PYTHON_BIN" \
    "$ROOT/pc_notify.py"
