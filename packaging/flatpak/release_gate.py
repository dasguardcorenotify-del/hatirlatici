#!/usr/bin/env python3
"""Deterministic, read-only public-release gate for Hatırlatıcı."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path


APP_ID = "io.github.dasguardcorenotify_del.hatirlatici"
VERSION = "2.0.0"
TAG = f"v{VERSION}"
RELEASE_ASSET = f"hatirlatici-{VERSION}.tar.xz"
RELEASE_URL = (
    "https://github.com/dasguardcorenotify-del/hatirlatici/"
    f"releases/download/{TAG}/{RELEASE_ASSET}"
)
SOURCE_DATE_EPOCH = 1787270400
ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_MANIFEST = ROOT / f"{APP_ID}.yml"
DEVELOPMENT_MANIFEST = ROOT / f"{APP_ID}.Devel.yml"
METAINFO = ROOT / "packaging" / "flatpak" / f"{APP_ID}.metainfo.xml"
DESKTOP = ROOT / "packaging" / "flatpak" / f"{APP_ID}.desktop"
SCREENSHOT_BASE = "https://raw.githubusercontent.com/dasguardcorenotify-del/hatirlatici/f01d9a27420cb41fc7e782a8aea96f66d6a9bb28/docs/screenshots"
SCREENSHOTS = (
    (
        "01-today-new-reminder.png",
        1000,
        700,
        "66a352135cc3c44214b9fd03546caa88a0a52313648da571e52cb3dd5ffa9bff",
        {
            "en": "Create a reminder from the Today view",
            "tr": "Bugün görünümünde yeni hatırlatıcı oluşturma",
            "de": "Eine Erinnerung in der Heute-Ansicht erstellen",
            "es": "Crear un recordatorio desde la vista Hoy",
            "ru": "Создание напоминания в представлении «Сегодня»",
        },
    ),
    (
        "02-reminder-list.png",
        1000,
        700,
        "9d8b309f598353acda6aa207ef427892589fb8e585e259d705525b0c95721d6f",
        {
            "en": "Review scheduled reminders in the list",
            "tr": "Planlanmış hatırlatıcıları listede gözden geçirme",
            "de": "Geplante Erinnerungen in der Liste prüfen",
            "es": "Revisar los recordatorios programados en la lista",
            "ru": "Просмотр запланированных напоминаний в списке",
        },
    ),
    (
        "03-history.png",
        1000,
        700,
        "b3c1c7383b6cabae7105784a4c6008235fd8dbc3feaac03e59ca562a639c21ad",
        {
            "en": "Review reminder delivery history",
            "tr": "Hatırlatıcı teslim geçmişini gözden geçirme",
            "de": "Den Zustellverlauf der Erinnerungen prüfen",
            "es": "Revisar el historial de entrega de recordatorios",
            "ru": "Просмотр истории доставки напоминаний",
        },
    ),
    (
        "04-settings-local-security.png",
        1000,
        700,
        "c631787053b723b5d47a3d891e96b61fec8a29c2a89979609c95ea544a42b062",
        {
            "en": "Configure language, delivery, and local security settings",
            "tr": "Dil, teslimat ve yerel güvenlik ayarlarını yapılandırma",
            "de": "Sprache, Zustellung und lokale Sicherheit konfigurieren",
            "es": "Configurar el idioma, la entrega y la seguridad local",
            "ru": "Настройка языка, доставки и локальной безопасности",
        },
    ),
    (
        "05-first-run-gmail-guide.png",
        980,
        730,
        "2995a7cee28cb2d338143e99c94a59a57ac19fa19566d61da8b09ed5d42bb142",
        {
            "en": "Follow the first-run Gmail App Password guide",
            "tr": "İlk çalıştırmada Gmail Uygulama Şifresi rehberini izleme",
            "de": "Der Anleitung für Gmail-App-Passwörter beim ersten Start folgen",
            "es": "Seguir la guía inicial de contraseñas de aplicación de Gmail",
            "ru": "Руководство по паролю приложения Gmail при первом запуске",
        },
    ),
    (
        "06-support-and-language.png",
        1000,
        700,
        "2b202503c120d401a383bc0f245afecd2fe1d06633dc34684a2fddb8018e5ce6",
        {
            "en": "Access About, privacy, issue-reporting, and support options",
            "tr": "Hakkında, gizlilik, sorun bildirme ve destek seçeneklerine erişme",
            "de": "Info, Datenschutz, Fehlerberichte und Support aufrufen",
            "es": "Acceder a Acerca de, privacidad, informes de errores y ayuda",
            "ru": "Доступ к сведениям, конфиденциальности, сообщениям об ошибках и поддержке",
        },
    ),
)
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

SKIP_DIRS = {
    ".flatpak-builder",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "qa-artifacts",
    "qa-output",
    "repo",
    "venv",
}
TEXT_SUFFIXES = {
    ".desktop",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
RUNTIME_FILENAMES = {
    "credentials.json",
    "hatirlatmalar.csv",
    "hatirlatici_history.csv",
    "pc_hatirlatmalar.csv",
    "settings.json",
    "settings_v2.json",
}


class GateFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise GateFailure(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_public_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part.startswith("build-") for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore"}:
            result.append(path)
    return sorted(result)


def privacy_and_secret_gate() -> None:
    private_path = re.compile(r"/(?:home|Users)/[^/\s]+")
    email = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
    private_key = re.compile("BEGIN " + r"(?:(?:RSA|EC|DSA|OPENSSH) )?PRIVATE KEY")
    github_token = re.compile("gh" + r"[pousr]_[A-Za-z0-9]{30,}")
    slack_token = re.compile("xox" + r"[abprs]-[A-Za-z0-9-]{20,}")
    aws_key = re.compile("AK" + r"IA[0-9A-Z]{16}")
    forbidden_env = [
        item
        for item in os.environ.get("HATIRLATICI_FORBIDDEN_LITERALS", "").split(os.pathsep)
        if item
    ]

    hits: list[str] = []
    for path in iter_public_files():
        relative = path.relative_to(ROOT)
        text = read_text(path)
        for line_number, line in enumerate(text.splitlines(), 1):
            if private_path.search(line):
                hits.append(f"{relative}:{line_number}: private absolute path")
            if private_key.search(line) or github_token.search(line) or slack_token.search(line) or aws_key.search(line):
                hits.append(f"{relative}:{line_number}: secret-shaped value")
            if path.name != "LICENSE":
                for address in email.findall(line):
                    domain = address.rsplit("@", 1)[1].lower()
                    if not domain.endswith((".invalid", ".test", ".example")):
                        hits.append(f"{relative}:{line_number}: public email literal")
            for literal in forbidden_env:
                if literal in line:
                    hits.append(f"{relative}:{line_number}: owner-supplied forbidden literal")

        if relative.name in RUNTIME_FILENAMES:
            hits.append(f"{relative}: runtime-data filename")

    if hits:
        fail("privacy/secret gate:\n" + "\n".join(hits))


def localization_gate() -> None:
    spec = importlib.util.spec_from_file_location("hatirlatici_release_l10n", ROOT / "l10n.py")
    if spec is None or spec.loader is None:
        fail("unable to load l10n.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_catalog()
    expected = {"en", "tr", "de", "es", "ru"}
    if set(module.SUPPORTED_LANGUAGES) != expected:
        fail(f"supported locale mismatch: {module.SUPPORTED_LANGUAGES!r}")


def hardcoded_ui_gate() -> None:
    call_names = {
        "QAction",
        "QCheckBox",
        "QGroupBox",
        "QLabel",
        "QPushButton",
        "QRadioButton",
        "_setting_card",
        "setAccessibleDescription",
        "setAccessibleName",
        "setPlaceholderText",
        "setStatusTip",
        "setText",
        "setTitle",
        "setToolTip",
        "setWindowTitle",
        "showMessage",
        "show_status",
    }
    allowed = {"HATIRLATICI", "Hatırlatıcı", VERSION, f"Hatırlatıcı {VERSION.rsplit('.', 1)[0]}"}
    hits: list[str] = []
    for relative in (Path("ui_v2/first_run_setup.py"), Path("ui_v2/hatirlatici_ultimate.py")):
        path = ROOT / relative
        tree = ast.parse(read_text(path), filename=str(relative))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            else:
                continue
            if name not in call_names:
                continue
            args = node.args[:2] if name == "_setting_card" else node.args[:1]
            for argument in args:
                if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                    continue
                value = argument.value.strip()
                if value and value not in allowed and any(character.isalpha() for character in value):
                    hits.append(f"{relative}:{node.lineno}:{name}")
    if hits:
        fail("hardcoded user-facing localization debt:\n" + "\n".join(hits))


def validate_url_hash_pairs(manifest_text: str) -> None:
    lines = manifest_text.splitlines()
    missing: list[int] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("url: http"):
            continue
        indent = len(line) - len(line.lstrip())
        found = False
        for later in lines[index + 1 : index + 7]:
            later_stripped = later.strip()
            later_indent = len(later) - len(later.lstrip())
            if later_stripped.startswith("- type:") and later_indent <= indent:
                break
            if re.fullmatch(r"sha256: [0-9a-f]{64}", later_stripped):
                found = True
                break
        if not found:
            missing.append(index + 1)
    if missing:
        fail(f"manifest URLs without adjacent SHA256: lines {missing}")


def finish_args(manifest_text: str) -> set[str]:
    """Return top-level finish-args in linear time.

    The previous multi-line regular expression could catastrophically
    backtrack on a large source-build manifest. Flatpak YAML here has a
    simple top-level contract, so scan lines once and stop at the next
    top-level key.
    """
    lines = manifest_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line == "finish-args:":
            start = index + 1
            break
    if start is None:
        fail("manifest has no finish-args block")

    result: set[str] = set()
    for line in lines[start:]:
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- --"):
            result.add(stripped[2:])
    return result


def screenshot_gate() -> None:
    try:
        component = ET.parse(METAINFO).getroot()
    except ET.ParseError as error:
        fail(f"invalid AppStream XML: {error}")

    screenshots = component.findall("./screenshots/screenshot")
    if len(screenshots) != len(SCREENSHOTS):
        fail(f"AppStream screenshot count mismatch: {len(screenshots)}")

    screenshot_dir = ROOT / "docs" / "screenshots"
    actual_local = {path.name for path in screenshot_dir.glob("*.png") if path.is_file()}
    expected_local = {spec[0] for spec in SCREENSHOTS}
    if actual_local != expected_local:
        fail(f"local screenshot set mismatch: {sorted(actual_local)!r}")

    for index, (node, spec) in enumerate(zip(screenshots, SCREENSHOTS, strict=True)):
        filename, width, height, expected_digest, expected_captions = spec
        expected_attributes = {"type": "default"} if index == 0 else {}
        if node.attrib != expected_attributes:
            fail(f"screenshot {filename} attributes mismatch: {node.attrib!r}")

        images = node.findall("image")
        if len(images) != 1:
            fail(f"screenshot {filename} must have exactly one source image")
        image = images[0]
        expected_image_attributes = {
            "type": "source",
            "width": str(width),
            "height": str(height),
        }
        if image.attrib != expected_image_attributes:
            fail(f"screenshot {filename} image attributes mismatch: {image.attrib!r}")
        if (image.text or "").strip() != f"{SCREENSHOT_BASE}/{filename}":
            fail(f"screenshot {filename} does not use its immutable v2.0.0 raw URL")

        captions: dict[str, str] = {}
        for caption in node.findall("caption"):
            language = caption.attrib.get(XML_LANG, "en")
            if language in captions:
                fail(f"duplicate {language} caption for screenshot {filename}")
            captions[language] = (caption.text or "").strip()
        if captions != expected_captions:
            fail(f"localized captions mismatch for screenshot {filename}")

        local_path = screenshot_dir / filename
        content = local_path.read_bytes()
        if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n" or content[12:16] != b"IHDR":
            fail(f"invalid PNG screenshot: {filename}")
        actual_width, actual_height = struct.unpack(">II", content[16:24])
        if (actual_width, actual_height) != (width, height):
            fail(
                f"screenshot dimensions mismatch for {filename}: "
                f"{actual_width}x{actual_height}"
            )
        if hashlib.sha256(content).hexdigest() != expected_digest:
            fail(f"approved screenshot digest mismatch: {filename}")


def packaging_gate() -> None:
    # Reject divergence of the dependency recipe even if individual marker
    # strings still happen to match. No build, network or publication here.
    pair_check = subprocess.run(
        [sys.executable, "-I", str(ROOT / "tools/manifest_contract.py"), "check", "--root", str(ROOT)],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    if pair_check.returncode:
        fail("production/development recipe mismatch: " + pair_check.stderr.strip())
    production = read_text(PRODUCTION_MANIFEST)
    development = read_text(DEVELOPMENT_MANIFEST)
    forbidden = (
        ".whl",
        "only-arches",
        "skip-arches",
        "--share=network\n      build-args",
        "base:",
        "base-version:",
        "--no-talk-name",
        "--nofilesystem",
        "--nosocket",
    )
    for value in forbidden:
        if value in production or value in development:
            fail(f"manifest contains forbidden value: {value}")
    if "type: dir" in production:
        fail("production manifest uses a mutable type: dir source")
    if "type: dir" not in development or "path: ." not in development:
        fail("development manifest does not identify the checkout source")
    if RELEASE_URL not in production:
        fail("production manifest release asset URL does not match version/tag contract")
    runtime_contract = (
        "runtime: org.freedesktop.Platform",
        "runtime-version: '26.08'",
        "sdk: org.freedesktop.Sdk",
        "qtbase-everywhere-src-6.11.1.tar.xz",
        "qtwayland-everywhere-src-6.11.1.tar.xz",
        "qtsvg-everywhere-src-6.11.1.tar.xz",
        "-DFEATURE_wayland_client=ON",
        "-DFEATURE_wayland_server=OFF",
        "-DFEATURE_glibc_fortify_source=OFF",
        "qtbase-client-only-contract",
        "QT_FEATURE_wayland_server=-1",
        "QT_FEATURE_glibc_fortify_source=-1",
        "FLATPAK_SDK_FORTIFY_SOURCE=3",
        "-DFEATURE_sql=OFF",
        "pyqt6-6.11.0.tar.gz",
        "packaging-26.3.tar.gz",
        "94edc256424af38762eb31306eed28beb9f0efc50a8837492c9d6fd6004aed79",
    )
    for marker in runtime_contract:
        if marker not in production or marker not in development:
            fail(f"source/runtime contract missing from a manifest: {marker}")
    for name, manifest in (("production", production), ("development", development)):
        if manifest.count("-DFEATURE_wayland_client=ON") != 1:
            fail(f"{name} must enable the QtBase Wayland client exactly once")
        if manifest.count("-DFEATURE_wayland_server=OFF") != 2:
            fail(f"{name} must disable the Wayland server in QtBase and QtWayland")
        if "-DQT_FEATURE_" in manifest:
            fail(f"{name} forces Qt's internal feature-cache namespace")
        if manifest.find("qtsvg-everywhere-src-6.11.1.tar.xz") > manifest.find(
            "qtwayland-everywhere-src-6.11.1.tar.xz"
        ):
            fail(f"{name} must build Qt SVG before QtWayland's Adwaita decoration plugin")
        if "/lib/libQt6OpenGL*.so*" in manifest:
            fail(f"{name} removes Qt OpenGL required by Wayland client plugins")
        if "- /lib/libQt6OpenGLWidgets.so*" not in manifest:
            fail(f"{name} does not remove the unused Qt OpenGL Widgets library")
        for cleanup_entry in (
            "- /lib64/pkgconfig",
            "- /lib/python*/site-packages/packaging*",
            "- /lib/python*/site-packages/cairo/include",
            "- /bin/cffi-gen-src",
            "- /bin/pylupdate6",
            "- /bin/pyuic6",
            "- /bin/sip-install",
            "- /plugins/wayland-graphics-integration-client/libdmabuf-server.so",
            "- /plugins/wayland-graphics-integration-client/libdrm-egl-server.so",
            "- /plugins/wayland-graphics-integration-client/libshm-emulation-server.so",
        ):
            if cleanup_entry not in manifest:
                fail(f"{name} build/development cleanup missing: {cleanup_entry}")
        for hardening_setting in (
            "QMAKE_CFLAGS_RELEASE += ${CFLAGS}",
            "QMAKE_CXXFLAGS_RELEASE += ${CXXFLAGS}",
            "QMAKE_LFLAGS += ${LDFLAGS}",
            "CONFIG += no_qt_rpath",
        ):
            if hardening_setting not in manifest:
                fail(f"{name} PyQt hardening setting missing: {hardening_setting}")
    expected_finish_args = {
        "--share=ipc",
        "--socket=wayland",
        "--socket=fallback-x11",
        "--device=dri",
        "--share=network",
        "--talk-name=org.kde.StatusNotifierWatcher",
    }
    for name, manifest in (("production", production), ("development", development)):
        actual = finish_args(manifest)
        if actual != expected_finish_args:
            fail(f"{name} finish-args mismatch: {sorted(actual)!r}")
        pyqt_modules = set(re.findall(r"--enable=(Qt[A-Za-z0-9]+)", manifest))
        expected_pyqt_modules = {"QtCore", "QtDBus", "QtGui", "QtNetwork", "QtWidgets"}
        if pyqt_modules != expected_pyqt_modules:
            fail(f"{name} PyQt module set mismatch: {sorted(pyqt_modules)!r}")
        for unwanted_qt_module in ("qtdeclarative", "qtwebengine", "qtmultimedia"):
            if unwanted_qt_module in manifest.lower():
                fail(f"{name} includes unwanted Qt module: {unwanted_qt_module}")
    validate_url_hash_pairs(production)
    validate_url_hash_pairs(development)

    for cargo_name in ("cargo-sources-maturin.json", "cargo-sources-cryptography.json"):
        cargo_path = ROOT / "packaging" / "flatpak" / cargo_name
        sources = json.loads(read_text(cargo_path))
        if not isinstance(sources, list) or not sources:
            fail(f"empty generated cargo source set: {cargo_name}")
        for source in sources:
            if source.get("type") == "archive":
                if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", ""))):
                    fail(f"unhashed Cargo archive in {cargo_name}")
            if "only-arches" in source or "skip-arches" in source:
                fail(f"architecture lock in {cargo_name}")

    metadata = read_text(METAINFO)
    required_metadata = (
        f"<id>{APP_ID}</id>",
        "<metadata_license>CC0-1.0</metadata_license>",
        "<project_license>GPL-3.0-or-later</project_license>",
        f'<release version="{VERSION}" date="2026-08-21">',
        f'<launchable type="desktop-id">{APP_ID}.desktop</launchable>',
        '<color type="primary" scheme_preference="light">#0E7C86</color>',
        '<color type="primary" scheme_preference="dark">#20C7C9</color>',
        '<control>keyboard</control>',
        '<control>pointing</control>',
        '<display_length compare="ge">768</display_length>',
        '<url type="details">https://github.com/dasguardcorenotify-del/hatirlatici/blob/f01d9a27420cb41fc7e782a8aea96f66d6a9bb28/docs/RELEASE_NOTES_2.0.0.md</url>',
    )
    for value in required_metadata:
        if value not in metadata:
            fail(f"missing AppStream release contract: {value}")
    if 'type="donation"' in metadata:
        fail("unverified donation metadata is present")
    screenshot_gate()
    if any(marker in metadata for marker in ("example.com", "REPLACE_ME", "TODO_URL")):
        fail("placeholder AppStream URL is present")

    desktop = read_text(DESKTOP)
    if f"Icon={APP_ID}" not in desktop or "Exec=hatirlatici" not in desktop:
        fail("desktop identity contract mismatch")

    launcher = read_text(ROOT / "packaging" / "flatpak" / "hatirlatici-flatpak-launcher.sh")
    if "${PYTHONPATH:+" in launcher or "export PYTHONNOUSERSITE=1" not in launcher:
        fail("Flatpak launcher inherits an untrusted Python module path")

    app_identity = read_text(ROOT / "app_identity.py")
    if '"org.freedesktop.Platform"' not in app_identity or '"26.08"' not in app_identity:
        fail("application runtime identity does not match the production manifest")


def external_metadata_gate() -> None:
    commands = (
        ("desktop-file-validate", str(DESKTOP)),
        ("appstreamcli", "validate", "--no-net", "--explain", str(METAINFO)),
    )
    for command in commands:
        try:
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        except FileNotFoundError:
            fail(f"required validator not installed: {command[0]}")
        if result.returncode:
            fail(f"{' '.join(command)} failed:\n{result.stdout}\n{result.stderr}")
        combined = (result.stdout + result.stderr).lower()
        if "warning:" in combined or "hint:" in combined:
            fail(f"{' '.join(command)} produced a warning/hint:\n{result.stdout}\n{result.stderr}")


def expected_archive_sources() -> set[Path]:
    sources = {path.relative_to(ROOT) for path in ROOT.glob("*.py") if path.is_file()}
    sources.update(path.relative_to(ROOT) for path in (ROOT / "ui_v2").rglob("*.py") if path.is_file())
    sources.update(path.relative_to(ROOT) for path in (ROOT / "tools").rglob("*.py") if path.is_file())
    for path in (ROOT / "tests").rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if path.suffix in {".py", ".sh"} or "fixtures" in relative.parts:
            sources.add(relative)
    fixed = {
        Path("assets/hatirlatici.svg"),
        Path("packaging/flatpak/hatirlatici-flatpak-launcher.sh"),
        Path(f"packaging/flatpak/{APP_ID}.desktop"),
        Path(f"packaging/flatpak/{APP_ID}.metainfo.xml"),
        Path(f"packaging/flatpak/{APP_ID}.svg"),
        Path("packaging/flatpak/cargo-sources-cryptography.json"),
        Path("packaging/flatpak/cargo-sources-maturin.json"),
        Path("packaging/flatpak/create-release-source.sh"),
        Path("packaging/flatpak/install-cargo-license-inventory.py"),
        Path(f"{APP_ID}.Devel.yml"),
        Path("LICENSE"),
        Path("README.md"),
        Path("README_TR.md"),
        Path("SECURITY.md"),
        Path("PRIVACY.md"),
        Path("CONTRIBUTING.md"),
        Path("CHANGELOG.md"),
        Path("SUPPORT.md"),
        Path("THIRD_PARTY_NOTICES.md"),
    }
    sources.update(fixed)
    missing = sorted(str(path) for path in sources if not (ROOT / path).is_file())
    if missing:
        fail(f"release archive source set has missing files: {missing!r}")
    return sources


def archive_gate(archive: Path) -> None:
    if archive.name != RELEASE_ASSET:
        fail(f"release archive must be named {RELEASE_ASSET}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    production = read_text(PRODUCTION_MANIFEST)
    url_position = production.find(RELEASE_URL)
    if url_position < 0:
        fail("release asset URL missing from production manifest")
    source_block = production[url_position : url_position + 512]
    if f"sha256: {digest}" not in source_block:
        fail("release archive digest does not match production manifest")

    prefix = f"hatirlatici-{VERSION}/"
    expected_sources = expected_archive_sources()
    expected_names = {prefix + path.as_posix() for path in expected_sources}
    with tarfile.open(archive, mode="r:xz") as handle:
        members = handle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            fail("duplicate member in source archive")
        if f"{prefix}{PRODUCTION_MANIFEST.name}" in names:
            fail("production manifest must be excluded from its hashed source archive")
        if set(names) != expected_names:
            missing = sorted(expected_names - set(names))
            extra = sorted(set(names) - expected_names)
            fail(f"release archive source-set mismatch; missing={missing!r}, extra={extra!r}")
        for member in members:
            if not member.name.startswith(prefix):
                fail(f"archive member outside versioned root: {member.name}")
            if not member.isfile():
                fail(f"non-regular archive member: {member.name}")
            if member.uid != 0 or member.gid != 0 or member.mtime != SOURCE_DATE_EPOCH:
                fail(f"non-deterministic archive metadata: {member.name}")
            if member.name.endswith((".pyc", ".pyo")) or "/__pycache__/" in member.name:
                fail(f"generated Python artifact in source archive: {member.name}")
            if Path(member.name).name in RUNTIME_FILENAMES:
                fail(f"runtime data in source archive: {member.name}")
            relative = Path(member.name.removeprefix(prefix))
            extracted = handle.extractfile(member)
            if extracted is None or extracted.read() != (ROOT / relative).read_bytes():
                fail(f"archive content differs from checkout: {member.name}")


def tag_gate() -> None:
    expected_origin = "https://github.com/dasguardcorenotify-del/hatirlatici.git"
    commands = {
        "head": ("git", "rev-parse", "HEAD"),
        "tag": ("git", "rev-list", "-n", "1", TAG),
        "origin": ("git", "remote", "get-url", "origin"),
    }
    values: dict[str, str] = {}
    for name, command in commands.items():
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode:
            fail(f"tag contract command failed: {' '.join(command)}")
        values[name] = result.stdout.strip()
    if values["head"] != values["tag"]:
        fail(f"{TAG} does not identify the checked-out source commit")
    # Keep the SSH spelling split so this scanner does not whitelist a
    # credential-like/public-email literal in its own source.
    ssh_origin_prefix = "git" + "@github.com:"
    normalized_origin = values["origin"].replace(ssh_origin_prefix, "https://github.com/")
    if normalized_origin.rstrip("/") not in {expected_origin, expected_origin.removesuffix(".git")}:
        fail("origin does not identify the canonical public repository")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="validate the deterministic release source archive")
    parser.add_argument("--require-tag", action="store_true", help="require v2.0.0 to point at HEAD and canonical origin")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = (
        ("PRIVACY_SECRET_GATE", privacy_and_secret_gate),
        ("LOCALIZATION_CATALOG_GATE", localization_gate),
        ("HARDCODED_UI_L10N_GATE", hardcoded_ui_gate),
        ("PACKAGING_SOURCE_GATE", packaging_gate),
        ("DESKTOP_METADATA_GATE", external_metadata_gate),
    )
    try:
        for label, check in checks:
            check()
            print(f"{label}=PASS")
        if args.archive is not None:
            archive_gate(args.archive.resolve())
            print("RELEASE_ARCHIVE_GATE=PASS")
        if args.require_tag:
            tag_gate()
            print("RELEASE_TAG_GATE=PASS")
    except (GateFailure, OSError, SyntaxError, ValueError) as exc:
        print(f"PUBLIC_RELEASE_GATE=FAIL\n{exc}", file=sys.stderr)
        return 1
    print("PUBLIC_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
