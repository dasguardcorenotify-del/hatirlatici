#!/usr/bin/env python3
"""Install a deterministic license inventory for vendored runtime Rust crates."""

# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path


LICENSE_NAME = re.compile(
    r"^(?:LICEN[CS]E|COPYING|NOTICE|UNLICENSE)(?:[._-].*)?$",
    re.IGNORECASE,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-count", required=True, type=int)
    args = parser.parse_args()

    vendor = args.vendor.resolve()
    output = args.output.resolve()
    crates = sorted(path for path in vendor.iterdir() if path.is_dir())
    if len(crates) != args.expected_count:
        raise SystemExit(
            f"expected {args.expected_count} vendored crates, found {len(crates)}"
        )

    output.mkdir(parents=True, exist_ok=True)
    packages: list[dict[str, object]] = []
    identities: set[tuple[str, str]] = set()
    for crate in crates:
        manifest_path = crate / "Cargo.toml"
        checksum_path = crate / ".cargo-checksum.json"
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        checksum = json.loads(checksum_path.read_text(encoding="utf-8"))
        package = manifest.get("package", {})
        name = str(package.get("name", "")).strip()
        version = str(package.get("version", "")).strip()
        license_expression = str(package.get("license", "")).strip()
        identity = (name, version)
        if not all(identity) or identity in identities:
            raise SystemExit(f"invalid or duplicate Cargo package identity: {identity!r}")
        if not license_expression:
            raise SystemExit(f"missing Cargo license expression: {name} {version}")
        source_sha256 = str(checksum.get("package", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise SystemExit(f"invalid source checksum: {name} {version}")
        identities.add(identity)

        license_paths = sorted(
            path for path in crate.iterdir() if path.is_file() and LICENSE_NAME.match(path.name)
        )
        declared_license_file = package.get("license-file")
        if declared_license_file:
            declared = (crate / str(declared_license_file)).resolve()
            if crate not in declared.parents or not declared.is_file():
                raise SystemExit(f"invalid declared license file: {name} {version}")
            if declared not in license_paths:
                license_paths.append(declared)
                license_paths.sort()
        if not license_paths:
            raise SystemExit(f"no bundled license text: {name} {version}")

        destination = output / f"{name}-{version}"
        destination.mkdir(mode=0o755, parents=True, exist_ok=True)
        installed_licenses: list[dict[str, str]] = []
        for source in license_paths:
            target = destination / source.name
            shutil.copyfile(source, target)
            target.chmod(0o644)
            installed_licenses.append({"file": source.name, "sha256": digest(target)})

        packages.append(
            {
                "name": name,
                "version": version,
                "license": license_expression,
                "repository": package.get("repository"),
                "source_sha256": source_sha256,
                "license_files": installed_licenses,
            }
        )

    report = {
        "schema": 1,
        "scope": "cryptography-50.0.0-runtime-cargo",
        "packages": sorted(packages, key=lambda item: (str(item["name"]), str(item["version"]))),
    }
    report_path = output / "CARGO_DEPENDENCIES.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.chmod(0o644)
    print(f"CRYPTOGRAPHY_CARGO_LICENSE_INVENTORY=PASS packages={len(packages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
