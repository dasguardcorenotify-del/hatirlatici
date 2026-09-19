#!/usr/bin/env python3
"""Deterministic off-screen geometry gate for the production main UI."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


PARSER = argparse.ArgumentParser()
PARSER.add_argument("--scale", required=True)
ARGS = PARSER.parse_args()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = ARGS.scale

CODE_ROOT_OVERRIDE = os.environ.get(
    "HATIRLATICI_MAIN_GEOMETRY_CODE_ROOT",
    "",
).strip()
if CODE_ROOT_OVERRIDE:
    ROOT = Path(CODE_ROOT_OVERRIDE).resolve()
    CODE_ROOT_SOURCE = "INSTALLED_OVERRIDE"
else:
    ROOT = Path(__file__).resolve().parent.parent
    CODE_ROOT_SOURCE = "CHECKOUT"
UI_ROOT = ROOT / "ui_v2"

# Runtime modules bind several data paths at import time.  Establish an
# isolated XDG tree before importing any application module so this visual
# audit can never read or write a real user profile.
RUNTIME_SANDBOX = tempfile.TemporaryDirectory(
    prefix="hatirlatici-main-ui-geometry-",
)
RUNTIME_ROOT = Path(RUNTIME_SANDBOX.name)
ISOLATED_DIRS = {
    "XDG_CONFIG_HOME": RUNTIME_ROOT / "config",
    "XDG_DATA_HOME": RUNTIME_ROOT / "data",
    "XDG_STATE_HOME": RUNTIME_ROOT / "state",
    "XDG_CACHE_HOME": RUNTIME_ROOT / "cache",
    "XDG_RUNTIME_DIR": RUNTIME_ROOT / "runtime",
    "HOME": RUNTIME_ROOT / "home",
    "TMPDIR": RUNTIME_ROOT / "tmp",
}
for environment_name, directory in ISOLATED_DIRS.items():
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    os.environ[environment_name] = str(directory)
tempfile.tempdir = str(ISOLATED_DIRS["TMPDIR"])

if not (
    (ROOT / "runtime_config.py").is_file()
    and (UI_ROOT / "hatirlatici_ultimate.py").is_file()
):
    print("MAIN_UI_GEOMETRY_GATE=FAIL_INVALID_CODE_ROOT")
    RUNTIME_SANDBOX.cleanup()
    raise SystemExit(41)

for path in (str(ROOT), str(UI_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QComboBox,
    QLabel,
    QScrollArea,
    QSystemTrayIcon,
)

import core_v2 as core
import hatirlatici_app
import premium_preview as base
import runtime_config
from hatirlatici_ultimate import (
    FinalPolishWindow,
    PremiumConfirmDialog,
    UltimateEditDialog,
)


SIZES = (
    (960, 680),
    (1000, 700),
    (1120, 760),
    (1280, 800),
    (1366, 768),
    (1536, 960),
)
PAGES = (
    "today",
    "reminders",
    "history",
    "settings",
)


def sample_group() -> dict[str, object]:
    now = dt.datetime.now().replace(second=0, microsecond=0)
    return {
        "pair_id": "geometry-sample",
        "channel": "both",
        "subject": "Quarterly planning and secure delivery review",
        "body": "Review the reminder delivery status.",
        "next_run": now,
        "repeat": "weekly",
        "category": "Sağlık",
        "enabled": True,
        "mail_row": {"send_count": "2", "last_sent": now.strftime(core.TIME_FMT)},
        "pc_row": {"send_count": "3", "last_sent": now.strftime(core.TIME_FMT)},
    }


def clipped_text(widget) -> tuple[int, int] | None:
    text = widget.text().strip()
    if not text or not any(character.isalpha() for character in text):
        return None
    if isinstance(widget, QLabel):
        if widget.wordWrap() or "<" in text:
            return None
        available = widget.contentsRect().width()
        required = widget.fontMetrics().horizontalAdvance(text)
    elif isinstance(widget, QAbstractButton):
        available = widget.width()
        required = widget.sizeHint().width()
    else:
        return None
    if required > available + 3:
        return required, available
    return None


def audit_widget(root, context: str, failures: list[str]) -> None:
    for scroll in root.findChildren(QScrollArea):
        maximum = scroll.horizontalScrollBar().maximum()
        if maximum > 0:
            content = scroll.widget()
            failures.append(
                f"HORIZONTAL_SCROLL:{context}:{scroll.objectName()}:{maximum}:"
                f"viewport={scroll.viewport().width()}:"
                f"content={content.width() if content is not None else -1}"
            )

    for widget_type in (QLabel, QAbstractButton):
        for widget in root.findChildren(widget_type):
            if not widget.isVisibleTo(root):
                continue
            clipped = clipped_text(widget)
            if clipped is not None:
                required, available = clipped
                failures.append(
                    "TEXT_CLIP:"
                    f"{context}:{type(widget).__name__}:{widget.objectName()}:"
                    f"required={required}:available={available}:text={widget.text()!r}"
                )

            parent = widget.parentWidget()
            if parent is not None:
                bounds = parent.contentsRect()
                geometry = widget.geometry()
                if (
                    geometry.left() < bounds.left() - 2
                    or geometry.right() > bounds.right() + 2
                ):
                    failures.append(
                        "CHILD_BOUNDS:"
                        f"{context}:{type(widget).__name__}:{widget.objectName()}:"
                        f"child={geometry.left()}..{geometry.right()}:"
                        f"parent={bounds.left()}..{bounds.right()}"
                    )

    for combo in root.findChildren(QComboBox):
        if not combo.isVisibleTo(root) or not combo.currentText():
            continue
        required = combo.fontMetrics().horizontalAdvance(combo.currentText()) + 46
        available = combo.width()
        if required > available + 3:
            failures.append(
                "COMBO_CLIP:"
                f"{context}:{combo.objectName()}:required={required}:"
                f"available={available}:text={combo.currentText()!r}"
            )


def assert_runtime_isolation() -> None:
    sandbox = RUNTIME_ROOT.resolve()
    runtime_paths = {
        "settings": runtime_config.settings_path(),
        "mail_csv": runtime_config.mail_csv_path(),
        "pc_csv": runtime_config.pc_csv_path(),
        "history": runtime_config.history_path(),
        "app_settings": runtime_config.app_settings_path(),
        "backups": runtime_config.data_backups_dir(),
        "locks": runtime_config.locks_dir(),
        "core_mail_csv": core.MAIL_CSV,
        "core_pc_csv": core.PC_CSV,
        "core_history": core.HISTORY_CSV,
        "core_settings": core.SETTINGS_JSON,
        "preview_mail_csv": base.CSV_PATH,
        "preview_backup": base.BACKUP_PATH,
    }
    escaped = {
        name: str(Path(path).resolve())
        for name, path in runtime_paths.items()
        if not Path(path).resolve().is_relative_to(sandbox)
    }
    if escaped:
        raise AssertionError(
            f"Geometry gate runtime path escaped sandbox: {escaped}"
        )


def run() -> int:
    assert_runtime_isolation()
    app = QApplication.instance() or QApplication([])
    failures: list[str] = []
    cases = 0
    group = sample_group()
    event = {
        "channel": "both",
        "sent_at": dt.datetime.now().strftime(core.TIME_FMT),
        "subject": "Quarterly planning and secure delivery review",
    }

    with (
        mock.patch.object(core, "load_groups", return_value=[group]),
        mock.patch.object(core, "load_history", return_value=[event]),
        mock.patch.object(core, "load_settings", return_value={}),
        mock.patch.object(hatirlatici_app, "service_active", return_value=True),
        mock.patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
    ):
        for language in ("tr", "en", "de", "es", "ru"):
            runtime_config.save_settings(
                {
                    "setup_complete": True,
                    "profile_name": "Ada Lovelace",
                    "language": language,
                    "default_channel": "both",
                }
            )
            window = FinalPolishWindow()
            window.show()

            for page_id in PAGES:
                window.switch_page(page_id)
                app.processEvents()
                for width, height in SIZES:
                    window.resize(width, height)
                    app.processEvents()
                    # A sidebar breakpoint can enqueue one additional Qt
                    # layout pass; audit the settled, user-visible geometry.
                    app.processEvents()
                    actual = (window.width(), window.height())
                    if actual != (width, height):
                        failures.append(
                            f"WINDOW_SIZE:{language}:{page_id}:"
                            f"{width}x{height}:actual={actual[0]}x{actual[1]}"
                        )
                    cases += 1
                    audit_widget(
                        window.sidebar,
                        f"{language}:sidebar:{width}x{height}",
                        failures,
                    )
                    audit_widget(
                        window.main_widget,
                        f"{language}:{page_id}:{width}x{height}",
                        failures,
                    )

            edit = UltimateEditDialog(window, group)
            edit.resize(720, 660)
            edit.show()
            app.processEvents()
            audit_widget(edit, f"{language}:edit-dialog", failures)
            edit.close()

            confirm = PremiumConfirmDialog(
                window,
                window._t("delete_reminder"),
                window._t("delete_confirm", subject=str(group["subject"])),
            )
            confirm.show()
            app.processEvents()
            audit_widget(confirm, f"{language}:confirm-dialog", failures)
            confirm.close()

            window.close()
            window.deleteLater()
            app.processEvents()

    for failure in failures:
        print(failure)
    print(f"MAIN_UI_GEOMETRY_CASES={cases}")
    print(f"MAIN_UI_GEOMETRY_FAILURES={len(failures)}")
    print(
        "MAIN_UI_GEOMETRY_GATE="
        + ("PASS" if not failures else "FAIL")
    )
    print(f"MAIN_UI_CODE_ROOT_SOURCE={CODE_ROOT_SOURCE}")
    return 0 if not failures else 1


def main() -> int:
    try:
        return run()
    finally:
        RUNTIME_SANDBOX.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
