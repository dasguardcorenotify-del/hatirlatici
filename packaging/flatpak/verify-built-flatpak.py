#!/usr/bin/env python3
"""Verify exported Flatpak permissions and source-built runtime artifacts."""

from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


APP_ID = "io.github.dasguardcorenotify_del.hatirlatici"
ROOT = Path(__file__).resolve().parents[2]
RUNTIME_SMOKE = r'''import cairo
import cffi
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from PyQt6 import QtCore, QtDBus, QtGui, QtNetwork, QtWidgets
import background_portal
import credential_vault
import portal_notifications
import secret_portal

# Exercise each shipped native Python dependency without contacting a bus,
# network endpoint, keyring, or real user profile.
variant = GLib.Variant("s", "hatirlatici")
assert variant.unpack() == "hatirlatici"
assert Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(b"ok")).read_bytes(2, None).get_data() == b"ok"
for portal_module in (background_portal, portal_notifications, secret_portal):
    assert portal_module._load_gio() == (Gio, GLib)
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
context = cairo.Context(surface)
context.set_source_rgba(0.1, 0.2, 0.3, 1.0)
context.paint()
surface.flush()
assert len(surface.get_data()) == 16
ffi = cffi.FFI()
assert ffi.new("int *", 7)[0] == 7
key = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=credential_vault.KDF_SALT,
    info=credential_vault.KEY_CONTEXT,
).derive(b"m" * 32)
assert key == credential_vault.derive_key(b"m" * 32)
nonce = bytes(range(12))
ciphertext = AESGCM(key).encrypt(nonce, b"runtime-smoke", b"aad")
assert AESGCM(key).decrypt(nonce, ciphertext, b"aad") == b"runtime-smoke"

app = QtGui.QGuiApplication([])
formats = {bytes(item).decode("ascii") for item in QtGui.QImageReader.supportedImageFormats()}
assert "svg" in formats, formats
icon = QtGui.QIcon("/app/lib/hatirlatici/assets/hatirlatici.svg")
assert not icon.isNull()
pixmap = icon.pixmap(64, 64)
assert not pixmap.isNull()
assert not pixmap.toImage().isNull()
assert QtCore.QT_VERSION_STR == "6.11.1", QtCore.QT_VERSION_STR
assert QtCore.PYQT_VERSION_STR == "6.11.0", QtCore.PYQT_VERSION_STR
plugin_paths = (
    "/app/plugins/platforms/libqwayland.so",
    "/app/plugins/platforms/libqxcb.so",
    "/app/plugins/wayland-shell-integration/libxdg-shell.so",
    "/app/plugins/wayland-decoration-client/libadwaita.so",
    "/app/plugins/wayland-graphics-integration-client/libqt-plugin-wayland-egl.so",
    "/app/plugins/xcbglintegrations/libqxcb-egl-integration.so",
    "/app/plugins/xcbglintegrations/libqxcb-glx-integration.so",
    "/app/plugins/iconengines/libqsvgicon.so",
    "/app/plugins/imageformats/libqsvg.so",
)
loaders = []
for plugin_path in plugin_paths:
    loader = QtCore.QPluginLoader(plugin_path)
    assert loader.load(), f"{plugin_path}: {loader.errorString()}"
    loaders.append(loader)
print("BUILT_RUNTIME_SMOKE=PASS Qt/PyQt/SVG/GI/cairo/cffi/cryptography=exercised plugins=loadable")'''


def values(metadata: configparser.ConfigParser, section: str, key: str) -> set[str]:
    raw = metadata.get(section, key, fallback="")
    return {item for item in raw.split(";") if item}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_elf_hardening(path: Path, errors: list[str]) -> None:
    try:
        program_headers = subprocess.run(
            ("readelf", "-W", "-l", str(path)),
            text=True,
            capture_output=True,
            check=False,
        )
        dynamic = subprocess.run(
            ("readelf", "-W", "-d", str(path)),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        errors.append("readelf is required for the ELF hardening gate")
        return
    if program_headers.returncode or dynamic.returncode:
        errors.append(f"unable to inspect ELF hardening: {path}")
        return

    stack_line = next(
        (line for line in program_headers.stdout.splitlines() if line.strip().startswith("GNU_STACK")),
        "",
    )
    stack_fields = stack_line.split()
    require(bool(stack_fields), f"missing GNU_STACK header: {path}", errors)
    if stack_fields:
        require("E" not in stack_fields[-2], f"executable stack: {path}", errors)
    require("GNU_RELRO" in program_headers.stdout, f"missing GNU_RELRO: {path}", errors)
    require(
        "BIND_NOW" in dynamic.stdout or bool(re.search(r"\(FLAGS_1\).*\bNOW\b", dynamic.stdout)),
        f"missing BIND_NOW/full RELRO: {path}",
        errors,
    )
    require(
        "(RPATH)" not in dynamic.stdout and "(RUNPATH)" not in dynamic.stdout,
        f"embedded RPATH/RUNPATH: {path}",
        errors,
    )


def verify_qtbase_builder_state(builder_state: Path) -> list[str]:
    errors: list[str] = []
    candidates = list((builder_state / "build").glob("qtbase-*/CMakeCache.txt"))
    require(bool(candidates), f"no QtBase CMakeCache below {builder_state}", errors)
    if errors:
        return errors

    cache_path = max(candidates, key=lambda path: path.stat().st_mtime_ns)
    cache = cache_path.read_text(encoding="utf-8", errors="replace")
    build_root = cache_path.parent
    header_path = build_root / "src/gui/qtgui-config_p.h"
    core_header_path = build_root / "src/corelib/global/qconfig_p.h"
    require(
        bool(re.search(r"(?m)^FEATURE_wayland_client:BOOL=ON$", cache))
        and bool(re.search(r"(?m)^QT_FEATURE_wayland_client:INTERNAL=ON$", cache)),
        f"QtBase cache does not prove supported-input/computed Wayland client ON: {cache_path}",
        errors,
    )
    require(
        bool(re.search(r"(?m)^FEATURE_wayland_server:BOOL=OFF$", cache))
        and bool(re.search(r"(?m)^QT_FEATURE_wayland_server:INTERNAL=OFF$", cache)),
        f"QtBase cache does not prove supported-input/computed Wayland server OFF: {cache_path}",
        errors,
    )
    require(
        bool(re.search(r"(?m)^FEATURE_glibc_fortify_source:BOOL=OFF$", cache))
        and bool(re.search(r"(?m)^QT_FEATURE_glibc_fortify_source:INTERNAL=OFF$", cache)),
        f"QtBase cache does not prove its lower internal fortification override disabled: {cache_path}",
        errors,
    )
    require(
        bool(re.search(r"(?m)^CMAKE_C_FLAGS:STRING=.*(?:^|[ ,])-Wp,-D_FORTIFY_SOURCE=3(?:$|[ ,])", cache)),
        f"QtBase cache does not retain Flatpak SDK _FORTIFY_SOURCE=3: {cache_path}",
        errors,
    )
    require(
        not bool(re.search(r"(?m)^QT_FEATURE_(?:wayland_client|wayland_server):UNINITIALIZED=", cache)),
        f"QtBase cache contains forced internal Wayland feature values: {cache_path}",
        errors,
    )
    require(header_path.is_file(), f"missing generated Qt feature header: {header_path}", errors)
    if header_path.is_file():
        header = header_path.read_text(encoding="utf-8", errors="replace")
        require(
            "#define QT_FEATURE_wayland_client 1" in header,
            "generated Qt feature header does not enable Wayland client",
            errors,
        )
        require(
            "#define QT_FEATURE_wayland_server -1" in header,
            "generated Qt feature header does not disable Wayland server",
            errors,
        )
    require(core_header_path.is_file(), f"missing generated Qt core feature header: {core_header_path}", errors)
    if core_header_path.is_file():
        core_header = core_header_path.read_text(encoding="utf-8", errors="replace")
        require(
            "#define QT_FEATURE_glibc_fortify_source -1" in core_header,
            "Qt generated core feature header still enables its internal fortification override",
            errors,
        )
    ninja_path = build_root / "build.ninja"
    require(ninja_path.is_file(), f"missing QtBase Ninja graph: {ninja_path}", errors)
    if ninja_path.is_file():
        ninja = ninja_path.read_text(encoding="utf-8", errors="replace")
        require(
            "-D_FORTIFY_SOURCE=2" not in ninja,
            "QtBase Ninja graph lowers fortification to level 2",
            errors,
        )
        require(
            "-U_FORTIFY_SOURCE" not in ninja,
            "QtBase Ninja graph undefines SDK fortification",
            errors,
        )
    for forbidden in (
        build_root / "lib/libQt6WaylandCompositor.so",
        build_root / "include/QtWaylandCompositor",
        build_root / "lib/cmake/Qt6WaylandCompositor",
        build_root / "qml/QtWayland/Compositor",
    ):
        require(not forbidden.exists(), f"QtBase compositor build artifact present: {forbidden}", errors)
    if not errors:
        print(f"QTBASE_CONFIG_CACHE=PASS {cache_path}")
    return errors


def verify(build_dir: Path) -> list[str]:
    errors: list[str] = []
    metadata_path = build_dir / "metadata"
    files = build_dir / "files"
    require(metadata_path.is_file(), f"missing {metadata_path}", errors)
    require(files.is_dir(), f"missing {files}", errors)
    if errors:
        return errors

    metadata = configparser.ConfigParser(interpolation=None)
    metadata.optionxform = str
    metadata.read(metadata_path, encoding="utf-8")

    require(metadata.get("Application", "name", fallback="") == APP_ID, "application ID mismatch", errors)
    runtime = metadata.get("Application", "runtime", fallback="")
    require(runtime.startswith("org.freedesktop.Platform/") and runtime.endswith("/26.08"), "runtime mismatch", errors)
    require(values(metadata, "Context", "shared") == {"ipc", "network"}, "unexpected shared permissions", errors)
    # Flatpak serializes fallback-x11 as both x11 and the fallback marker. The
    # latter makes X11 unavailable when the Wayland socket is usable.
    require(
        values(metadata, "Context", "sockets") == {"x11", "wayland", "fallback-x11"},
        "unexpected socket permissions",
        errors,
    )
    require(values(metadata, "Context", "devices") == {"dri"}, "unexpected device permissions", errors)
    require(values(metadata, "Context", "filesystems") == set(), "unexpected filesystem permissions", errors)

    expected_session_bus = {"org.kde.StatusNotifierWatcher": "talk"}
    actual_session_bus = dict(metadata.items("Session Bus Policy")) if metadata.has_section("Session Bus Policy") else {}
    require(actual_session_bus == expected_session_bus, "unexpected session-bus policy", errors)
    require(not metadata.has_section("System Bus Policy"), "unexpected system-bus policy", errors)

    python_site_candidates = sorted(files.glob("lib/python3.*/site-packages"))
    require(
        len(python_site_candidates) == 1,
        f"Python site-packages contract mismatch: {python_site_candidates!r}",
        errors,
    )
    if len(python_site_candidates) == 1:
        site_packages = python_site_candidates[0]
        python_dir = site_packages.parent.name
        python_match = re.fullmatch(r"python(\d+)\.(\d+)", python_dir)
        require(python_match is not None, f"unexpected Python runtime directory: {python_dir}", errors)
        python_abi = "".join(python_match.groups()) if python_match is not None else "INVALID"
    else:
        site_packages = files / "lib/python-invalid/site-packages"
        python_dir = "python-invalid"
        python_abi = "INVALID"

    required_files = (
        "lib/libQt6Core.so.6.11.1",
        "lib/libQt6DBus.so.6.11.1",
        "lib/libQt6Gui.so.6.11.1",
        "lib/libQt6Network.so.6.11.1",
        "lib/libQt6OpenGL.so.6.11.1",
        "lib/libQt6Widgets.so.6.11.1",
        "lib/libQt6WaylandClient.so.6.11.1",
        "lib/libQt6Svg.so.6.11.1",
        "plugins/platforms/libqwayland.so",
        "plugins/platforms/libqxcb.so",
        "plugins/wayland-shell-integration/libxdg-shell.so",
        "plugins/wayland-decoration-client/libadwaita.so",
        "plugins/wayland-graphics-integration-client/libqt-plugin-wayland-egl.so",
        "plugins/xcbglintegrations/libqxcb-egl-integration.so",
        "plugins/xcbglintegrations/libqxcb-glx-integration.so",
        "plugins/iconengines/libqsvgicon.so",
        "plugins/imageformats/libqsvg.so",
        f"lib/{python_dir}/site-packages/PyQt6/QtCore.abi3.so",
        f"lib/{python_dir}/site-packages/PyQt6/QtDBus.abi3.so",
        f"lib/{python_dir}/site-packages/PyQt6/QtGui.abi3.so",
        f"lib/{python_dir}/site-packages/PyQt6/QtNetwork.abi3.so",
        f"lib/{python_dir}/site-packages/PyQt6/QtWidgets.abi3.so",
    )
    for relative in required_files:
        require((files / relative).is_file(), f"missing runtime artifact: {relative}", errors)

    pyqt_root = site_packages / "PyQt6"
    actual_bindings = {path.stem.split(".", 1)[0] for path in pyqt_root.glob("Qt*.abi3.so")}
    expected_bindings = {"QtCore", "QtDBus", "QtGui", "QtNetwork", "QtWidgets"}
    require(actual_bindings == expected_bindings, f"unexpected PyQt binding set: {sorted(actual_bindings)!r}", errors)
    for binding in expected_bindings:
        verify_elf_hardening(pyqt_root / f"{binding}.abi3.so", errors)

    native_extension_contract = (
        f"PyQt6/sip.cpython-{python_abi}-*.so",
        f"_cffi_backend.cpython-{python_abi}-*.so",
        f"cairo/_cairo.cpython-{python_abi}-*.so",
        "cryptography/hazmat/bindings/_rust.abi3.so",
        f"gi/_gi.cpython-{python_abi}-*.so",
        f"gi/_gi_cairo.cpython-{python_abi}-*.so",
    )
    for pattern in native_extension_contract:
        matches = list(site_packages.glob(pattern))
        require(len(matches) == 1, f"native extension contract mismatch for {pattern}: {matches!r}", errors)
    for extension in site_packages.glob("**/*.so"):
        verify_elf_hardening(extension, errors)

    forbidden_globs = (
        "lib/libQt6WaylandCompositor*",
        "lib/libQt6Concurrent*",
        "lib/libQt6OpenGLWidgets*",
        "lib/libQt6PrintSupport*",
        "lib/libQt6Sql*",
        "lib/libQt6SvgWidgets*",
        "lib/libQt6Test*",
        "lib/libQt6Xml*",
        "lib/libQt6Qml*",
        "lib/libQt6Quick*",
        "lib/libQt6WebEngine*",
        "lib/libQt6Multimedia*",
        "qml/QtWayland/Compositor/**",
        "plugins/wayland-graphics-integration-client/*server*.so",
        "lib/python*/site-packages/PyQt6/QtWebEngine*",
        "lib/python*/site-packages/PyQt6/QtMultimedia*",
        "include/**",
        "lib/cmake/**",
        "lib/pkgconfig/**",
        "lib64/pkgconfig/**",
        "lib/python*/site-packages/packaging*",
        "lib/python*/site-packages/cairo/include/**",
        "**/*.a",
        "**/*.la",
    )
    for pattern in forbidden_globs:
        if any(files.glob(pattern)):
            errors.append(f"forbidden runtime artifact: {pattern}")

    for build_tool in ("sip-build", "maturin", "qmake", "qmake6", "moc", "rcc", "uic"):
        require(not (files / "bin" / build_tool).exists(), f"build tool retained: {build_tool}", errors)
    exported_bin = {path.name for path in (files / "bin").iterdir()} if (files / "bin").is_dir() else set()
    require(exported_bin == {"hatirlatici"}, f"unexpected /app/bin set: {sorted(exported_bin)!r}", errors)

    license_root = files / "share" / "licenses" / APP_ID
    required_licenses = (
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "Qt6/LGPL-3.0-only.txt",
        "Qt6/FEATURES.txt",
        "Qt6-Wayland/LGPL-3.0-only.txt",
        "Qt6-SVG/LGPL-3.0-only.txt",
        "PyQt6/LICENSE",
        "PyQt6-sip/LICENSE",
        "sip/LICENSE",
        "PyQt-builder/LICENSE",
        "packaging/LICENSE",
        "packaging/LICENSE.APACHE",
        "packaging/LICENSE.BSD",
        "ply/README.md",
        "pycairo/COPYING",
        "pycairo/COPYING-LGPL-2.1",
        "pycairo/COPYING-MPL-1.1",
        "PyGObject/COPYING",
        "pycparser/LICENSE",
        "cffi/LICENSE",
        "cryptography/LICENSE",
        "cryptography/LICENSE.APACHE",
        "cryptography/LICENSE.BSD",
        "cryptography/cargo/CARGO_DEPENDENCIES.json",
    )
    for relative in required_licenses:
        require((license_root / relative).is_file(), f"missing installed license: {relative}", errors)
    feature_attestation = license_root / "Qt6/FEATURES.txt"
    if feature_attestation.is_file():
        require(
            feature_attestation.read_text(encoding="utf-8")
            == (
                "QtBase=6.11.1\n"
                "QT_FEATURE_wayland_client=1\n"
                "QT_FEATURE_wayland_server=-1\n"
                "QT_FEATURE_glibc_fortify_source=-1\n"
                "FLATPAK_SDK_FORTIFY_SOURCE=3\n"
            ),
            "QtBase client-only feature attestation mismatch",
            errors,
        )

    cargo_root = license_root / "cryptography/cargo"
    cargo_report_path = cargo_root / "CARGO_DEPENDENCIES.json"
    if cargo_report_path.is_file():
        try:
            cargo_report = json.loads(cargo_report_path.read_text(encoding="utf-8"))
            cargo_sources = json.loads(
                (ROOT / "packaging/flatpak/cargo-sources-cryptography.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, ValueError) as error:
            errors.append(f"invalid cryptography Cargo license inventory: {error}")
        else:
            expected_crates = {
                Path(source["dest"]).name: source["sha256"]
                for source in cargo_sources
                if source.get("type") == "archive"
            }
            require(cargo_report.get("schema") == 1, "Cargo license report schema mismatch", errors)
            require(
                cargo_report.get("scope") == "cryptography-50.0.0-runtime-cargo",
                "Cargo license report scope mismatch",
                errors,
            )
            packages = cargo_report.get("packages")
            require(isinstance(packages, list), "Cargo license report packages missing", errors)
            actual_crates: dict[str, str] = {}
            if isinstance(packages, list):
                for package in packages:
                    if not isinstance(package, dict):
                        errors.append("invalid Cargo license package entry")
                        continue
                    crate_id = f"{package.get('name', '')}-{package.get('version', '')}"
                    source_sha256 = str(package.get("source_sha256", ""))
                    if crate_id in actual_crates:
                        errors.append(f"duplicate Cargo license package: {crate_id}")
                    actual_crates[crate_id] = source_sha256
                    require(bool(package.get("license")), f"missing Cargo license: {crate_id}", errors)
                    license_files = package.get("license_files")
                    require(
                        isinstance(license_files, list) and bool(license_files),
                        f"missing bundled Cargo license text: {crate_id}",
                        errors,
                    )
                    if isinstance(license_files, list):
                        for license_file in license_files:
                            if not isinstance(license_file, dict):
                                errors.append(f"invalid Cargo license file entry: {crate_id}")
                                continue
                            filename = str(license_file.get("file", ""))
                            target = cargo_root / crate_id / filename
                            require(
                                bool(filename) and Path(filename).name == filename and target.is_file(),
                                f"missing installed Cargo license file: {crate_id}/{filename}",
                                errors,
                            )
                            if target.is_file():
                                require(
                                    hashlib.sha256(target.read_bytes()).hexdigest()
                                    == license_file.get("sha256"),
                                    f"Cargo license digest mismatch: {crate_id}/{filename}",
                                    errors,
                                )
            require(actual_crates == expected_crates, "Cargo license/source set mismatch", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_dir", type=Path)
    parser.add_argument("--manifest", type=Path, help="also run isolated PyQt/SVG rendering smoke test")
    parser.add_argument(
        "--builder-state",
        type=Path,
        help="also verify the newest QtBase CMake cache and generated feature header",
    )
    args = parser.parse_args()
    build_dir = args.build_dir.resolve()
    errors = verify(build_dir)
    if args.builder_state is not None:
        errors.extend(verify_qtbase_builder_state(args.builder_state.resolve()))
    if not errors and args.manifest is not None:
        command = (
            "flatpak-builder",
            "--run",
            str(build_dir),
            str(args.manifest.resolve()),
            "env",
            "QT_QPA_PLATFORM=offscreen",
            "XDG_CONFIG_HOME=/tmp/hatirlatici-smoke-config",
            "XDG_DATA_HOME=/tmp/hatirlatici-smoke-data",
            "XDG_CACHE_HOME=/tmp/hatirlatici-smoke-cache",
            "XDG_STATE_HOME=/tmp/hatirlatici-smoke-state",
            "HOME=/tmp/hatirlatici-smoke-home",
            "TMPDIR=/tmp/hatirlatici-smoke-tmp",
            "PYTHONNOUSERSITE=1",
            "PYTHONPATH=/app/lib/hatirlatici",
            "python3",
            "-c",
            RUNTIME_SMOKE,
        )
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        if result.returncode:
            errors.append(f"isolated runtime/SVG smoke failed:\n{result.stdout}\n{result.stderr}")
        else:
            print(result.stdout.strip())
    if errors:
        print("BUILT_FLATPAK_GATE=FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BUILT_FLATPAK_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
