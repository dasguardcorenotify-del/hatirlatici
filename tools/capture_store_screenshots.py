#!/usr/bin/env python3
"""Capture sanitized store screenshots from an isolated synthetic profile.

This utility is intentionally X11-only: it activates the real application
window and captures that exact X11 frame directly, without selecting or
cropping a desktop region.  Runtime paths are redirected before any
application module is imported.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PARSER = argparse.ArgumentParser()
PARSER.add_argument(
    "--scene",
    required=True,
    choices=(
        "today",
        "reminders",
        "history",
        "settings",
        "gmail-guide",
        "support",
    ),
)
PARSER.add_argument("--output", required=True, type=Path)
ARGS = PARSER.parse_args()

ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "ui_v2"
for candidate in (ROOT, UI_ROOT):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

RUNTIME_SANDBOX = tempfile.TemporaryDirectory(
    prefix="hatirlatici-store-capture-",
)
RUNTIME_ROOT = Path(RUNTIME_SANDBOX.name)
os.environ["XDG_CONFIG_HOME"] = str(RUNTIME_ROOT / "config")
os.environ["XDG_DATA_HOME"] = str(RUNTIME_ROOT / "data")
os.environ["XDG_STATE_HOME"] = str(RUNTIME_ROOT / "state")
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"


from unittest import mock

from PyQt6.QtCore import QDate, QTimer, QTime, Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QScrollArea,
    QSystemTrayIcon,
    QWidget,
)

import app_identity
import runtime_config
import core_v2 as core
import first_run_setup
import hatirlatici_app
import premium_preview as base
from hatirlatici_ultimate import FinalPolishWindow, ICON_PATH


def _assert_isolated() -> None:
    sandbox = RUNTIME_ROOT.resolve()
    paths = (
        runtime_config.settings_path(),
        runtime_config.mail_csv_path(),
        runtime_config.pc_csv_path(),
        runtime_config.history_path(),
        runtime_config.app_settings_path(),
        runtime_config.data_backups_dir(),
        runtime_config.locks_dir(),
        core.MAIL_CSV,
        core.PC_CSV,
        core.HISTORY_CSV,
        core.SETTINGS_JSON,
        base.CSV_PATH,
        base.BACKUP_PATH,
    )
    escaped = [
        str(Path(path).resolve())
        for path in paths
        if not Path(path).resolve().is_relative_to(sandbox)
    ]
    if escaped:
        raise RuntimeError(
            f"Screenshot runtime path escaped its sandbox: {escaped}"
        )


def _seed_profile() -> None:
    runtime_config.save_settings(
        {
            "setup_complete": True,
            "profile_name": "",
            "language": "en",
            "default_channel": "both",
            "smtp_provider": "gmail",
            "background_allowed": True,
            "background_autostart": True,
        }
    )
    core.save_settings(
        {
            "default_channel": "both",
            "default_category": "İş",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "minimize_to_tray": True,
        }
    )

    now = dt.datetime.now().replace(second=0, microsecond=0)
    today = now.replace(hour=23, minute=55)
    if today <= now:
        today = now + dt.timedelta(minutes=5)
    tomorrow = (now + dt.timedelta(days=1)).replace(
        hour=9,
        minute=30,
    )
    next_week = (now + dt.timedelta(days=4)).replace(
        hour=14,
        minute=0,
    )
    later = (now + dt.timedelta(days=7)).replace(
        hour=11,
        minute=15,
    )

    first = core.save_group(
        pair_id=None,
        channel="both",
        subject="Review the release checklist",
        body="Confirm screenshots, translations, and release notes.",
        run_at=today,
        repeat="once",
        category="İş",
    )
    second = core.save_group(
        pair_id=None,
        channel="pc",
        subject="Prepare the weekly planning notes",
        body="Collect priorities for the next team planning session.",
        run_at=tomorrow,
        repeat="weekly",
        category="Genel",
    )
    third = core.save_group(
        pair_id=None,
        channel="email",
        subject="Renew the library membership",
        body="Review the renewal details before the due date.",
        run_at=next_week,
        repeat="once",
        category="Kişisel",
    )
    paused = core.save_group(
        pair_id=None,
        channel="both",
        subject="Schedule the annual health check",
        body="Choose a convenient appointment time.",
        run_at=later,
        repeat="monthly",
        category="Sağlık",
    )
    core.set_group_enabled(paused, False)

    sent_counts = {
        first: 1,
        second: 1,
        third: 1,
    }
    last_sent = (now - dt.timedelta(hours=2)).strftime(core.TIME_FMT)
    for path, lock in (
        (core.MAIL_CSV, core.MAIL_LOCK),
        (core.PC_CSV, core.PC_LOCK),
    ):
        with core.exclusive(lock):
            fields, rows = core.read_csv(path, core.FIELDS)
            for row in rows:
                pair_id = str(row.get("pair_id") or "")
                if pair_id not in sent_counts:
                    continue
                row["send_count"] = str(sent_counts[pair_id])
                row["last_sent"] = last_sent
            core.atomic_write(path, fields, rows)

    history_rows = (
        (
            first,
            "both",
            now - dt.timedelta(hours=2),
            "Send the project status update",
            "Work",
            "completed",
        ),
        (
            second,
            "pc",
            now - dt.timedelta(days=1, hours=3),
            "Back up the presentation files",
            "General",
            "sent",
        ),
        (
            third,
            "email",
            now - dt.timedelta(days=2, hours=1),
            "Review the monthly budget",
            "Payment",
            "sent",
        ),
    )
    category_by_label = {
        "Work": "İş",
        "General": "Genel",
        "Payment": "Ödeme",
    }
    for pair_id, channel, sent_at, subject, label, action in history_rows:
        core.append_history(
            pair_id=pair_id,
            channel=channel,
            sent_at=sent_at.strftime(core.TIME_FMT),
            subject=subject,
            body=subject,
            category=category_by_label[label],
            action=action,
        )


def _center(window) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    window.move(
        area.x() + (area.width() - window.width()) // 2,
        area.y() + (area.height() - window.height()) // 2,
    )


def _build_window():
    if ARGS.scene == "gmail-guide":
        dialog = first_run_setup.GuidedFirstRunDialog(
            force=True,
            preview=True,
        )
        dialog.resize(960, 680)
        dialog._set_channel("both")
        dialog._set_provider("gmail")
        dialog.pages.setCurrentIndex(3)
        dialog._update_navigation()
        return dialog

    window = FinalPolishWindow()
    window.resize(1000, 700)

    if ARGS.scene == "today":
        tomorrow = (
            dt.datetime.now()
            + dt.timedelta(days=1)
        ).replace(
            hour=9,
            minute=30,
            second=0,
            microsecond=0,
        )
        window.subject_edit.setText(
            "Review the launch checklist"
        )
        window.note_edit.setPlainText(
            "Confirm screenshots and release notes."
        )
        window.date_edit.setDate(
            QDate(
                tomorrow.year,
                tomorrow.month,
                tomorrow.day,
            )
        )
        window.time_edit.setTime(
            QTime(9, 30)
        )
        window.repeat_combo.setCurrentIndex(
            max(
                0,
                window.repeat_combo.findData("weekly"),
            )
        )
        if getattr(window, "category_combo", None) is not None:
            window.category_combo.setCurrentIndex(
                max(
                    0,
                    window.category_combo.findData("İş"),
                )
            )
        both = window.delivery_group.button(2)
        if both is not None:
            both.setChecked(True)
    return window


def _capture(window, app: QApplication) -> None:
    if ARGS.scene in {"reminders", "history"}:
        window.switch_page(ARGS.scene)
    elif ARGS.scene in {"settings", "support"}:
        window.switch_page("settings")
    app.processEvents()
    QTest.qWait(900)

    if ARGS.scene == "support":
        scroll = window.findChild(
            QScrollArea,
            "ResponsivePageScroll",
        )
        if scroll is not None:
            scroll.verticalScrollBar().setValue(
                scroll.verticalScrollBar().maximum()
            )

    app.processEvents()
    window.raise_()
    window.activateWindow()
    app.processEvents()

    window_id = str(int(window.winId()))
    subprocess.run(
        [
            "xdotool",
            "windowactivate",
            "--sync",
            window_id,
        ],
        check=True,
        env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
    )
    window.update()
    for child in window.findChildren(QWidget):
        child.update()
    window.repaint()
    app.processEvents()
    QTest.qWait(1400)

    ARGS.output.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )
    if ARGS.scene == "gmail-guide":
        subprocess.run(
            [
                "import",
                "-silent",
                "-frame",
                "-window",
                window_id,
                str(ARGS.output),
            ],
            check=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
        )
    else:
        # The production main window is intentionally frameless and
        # translucent.  Some Cinnamon compositors return only accumulated
        # XDamage regions for direct window screenshots.  QWidget.grab()
        # forces a complete draw of that exact visible top-level and all its
        # children, preserving its custom frame and in-window shadow.
        pixmap = window.grab()
        if pixmap.isNull() or not pixmap.save(str(ARGS.output), "PNG"):
            raise RuntimeError("The application window could not be captured")
    print(f"SCREENSHOT_SCENE={ARGS.scene}")
    print(f"SCREENSHOT_OUTPUT={ARGS.output}")
    print("SCREENSHOT_RUNTIME_ISOLATED=YES")
    app.quit()


def main() -> int:
    _assert_isolated()
    _seed_profile()

    app = QApplication(sys.argv[:1])
    app.setApplicationName(app_identity.APP_ID)
    app.setApplicationVersion(app_identity.APP_VERSION)
    app.setApplicationDisplayName(base.ui_text("app_name", "en"))
    app.setDesktopFileName(app_identity.APP_ID)
    app.setOrganizationDomain(app_identity.ORGANIZATION_DOMAIN)
    app.setStyle("Fusion")
    app.setFont(QFont(base.select_font(), 10))
    app.setWindowIcon(QIcon(str(ICON_PATH)))

    with (
        mock.patch.object(
            hatirlatici_app,
            "service_active",
            return_value=True,
        ),
        mock.patch.object(
            QSystemTrayIcon,
            "isSystemTrayAvailable",
            return_value=False,
        ),
    ):
        window = _build_window()
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        window.show()
        _center(window)
        QTimer.singleShot(
            1400,
            lambda: _capture(window, app),
        )
        return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        RUNTIME_SANDBOX.cleanup()
