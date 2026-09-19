#!/usr/bin/env bash
set -euo pipefail

# Source archive only; does not build, publish, change a Git tag or overwrite
# an existing artifact. Production is excluded to avoid a circular checksum.
# modes/ownership/mtime are canonical, independent of the checkout's chmod.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${1:-${ROOT}/dist}"
mkdir -p -- "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
python3 -I "$ROOT/tools/manifest_contract.py" archive \
    --root "$ROOT" --output "$OUTPUT_DIR/hatirlatici-2.0.0.tar.xz"
sha256sum "$OUTPUT_DIR/hatirlatici-2.0.0.tar.xz"
