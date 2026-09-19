#!/usr/bin/env python3
"""Production application entry point and final interaction layer.

This module intentionally contains only advanced reminder actions, quick
entry, responsive composition, tray lifecycle, and process orchestration.
The reusable shell lives in ``premium_preview`` and data-backed pages in
``hatirlatici_app``.  Keeping one explicit responsibility per layer avoids
the former import-time patch stack while preserving reminder behavior.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

import runtime_config
from typing import Dict

from PyQt6.QtCore import QDate, QSize, Qt, QTime, QTimer, QUrl
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QBoxLayout,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

import core_v2 as core
import l10n
import premium_preview as base
from hatirlatici_app import (
    FinalWindow,
    channel_icon,
    channel_label,
)
from quick_parser import parse_quick
from language_menu import LanguageMenuButton
import app_identity
from delivery_scheduler import DeliveryScheduler
from mail_scheduler import MailDeliveryScheduler


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)
ICON_PATH = ROOT / "assets" / "hatirlatici.svg"
SINGLE_INSTANCE_OWNER_LOCK = (
    app_identity.SINGLE_INSTANCE_OWNER_LOCK
)
SUPPORT_LINKS = (
    (
        "source_repository",
        app_identity.SOURCE_REPOSITORY_URL,
    ),
    (
        "privacy_policy",
        app_identity.PRIVACY_URL,
    ),
    (
        "report_issue",
        app_identity.ISSUES_URL,
    ),
    (
        "support_help",
        app_identity.SUPPORT_URL,
    ),
)


def pc_delivery_status_key(
    status: str,
) -> str | None:
    if (
        status.startswith("pc-error:")
        or status == "pc-script-missing"
    ):
        return "notification_delivery_failed"
    return None


def single_instance_owner_lock_path() -> Path:
    return (
        runtime_config.locks_dir()
        / SINGLE_INSTANCE_OWNER_LOCK
    )


def try_acquire_owner_lock():
    """Return a locked 0600 handle, or ``None`` without blocking.

    The caller owns the returned handle for its full process lifetime and
    must unlock/close it on shutdown.  Public launch/setup coordination can
    use this same contract without touching the local-socket endpoint.
    """
    runtime_config.ensure_runtime_dirs()
    lock_path = single_instance_owner_lock_path()
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    lock_fd = os.open(
        lock_path,
        flags,
        0o600,
    )
    os.fchmod(lock_fd, 0o600)
    lock_handle = os.fdopen(
        lock_fd,
        "a+",
    )
    try:
        fcntl.flock(
            lock_handle.fileno(),
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        lock_handle.close()
        return None
    return lock_handle


class PremiumConfirmDialog(QDialog):
    def __init__(
        self,
        parent,
        title: str,
        message: str,
        accept_text: str | None = None,
    ):
        super().__init__(parent)
        language = getattr(
            parent,
            "language",
            base.runtime_language(),
        )

        self.setModal(True)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setMinimumWidth(450)
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            26,
            24,
            26,
            22,
        )
        layout.setSpacing(16)

        heading = QLabel(title)
        heading.setObjectName("PageTitle")

        detail = QLabel(message)
        detail.setObjectName("PageSub")
        detail.setWordWrap(True)

        buttons = QHBoxLayout()

        cancel = QPushButton(
            base.ui_text(
                "cancel",
                language,
            )
        )
        cancel.setObjectName("SecondaryButton")

        accept = QPushButton(
            accept_text
            or base.ui_text(
                "delete",
                language,
            )
        )
        accept.setObjectName("DangerButton")

        cancel.clicked.connect(self.reject)
        accept.clicked.connect(self.accept)

        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(accept)

        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addLayout(buttons)


class UltimateEditDialog(QDialog):
    def __init__(
        self,
        parent,
        group: Dict[str, object],
    ):
        super().__init__(parent)

        self.group = group
        self.language = getattr(
            parent,
            "language",
            base.runtime_language(),
        )

        def t(key: str, **values: object) -> str:
            return base.ui_text(
                key,
                self.language,
                **values,
            )

        self._t = t

        self.setModal(True)
        self.setWindowTitle(
            self._t("edit_reminder")
        )
        self.setWindowIcon(
            QIcon(str(ICON_PATH))
        )
        self.setMinimumWidth(610)
        self.setStyleSheet(
            parent.styleSheet()
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            26,
            24,
            26,
            22,
        )
        layout.setSpacing(9)

        title = QLabel(
            self._t("edit_reminder")
        )
        title.setObjectName("PageTitle")

        layout.addWidget(title)

        layout.addWidget(
            QLabel(self._t("subject_label"))
        )

        self.subject = QLineEdit(
            str(
                group.get("subject")
                or ""
            )
        )
        self.subject.setObjectName(
            "TextInput"
        )
        self.subject.setMinimumHeight(46)

        layout.addWidget(self.subject)

        datetime_row = QHBoxLayout()

        date_col = QVBoxLayout()
        date_col.addWidget(
            QLabel(self._t("date"))
        )

        self.date = QDateEdit()
        self.date.setObjectName("DateInput")
        self.date.setCalendarPopup(True)
        self.date.setLocale(
            base.qt_locale(self.language)
        )
        self.date.setDisplayFormat(
            "dd MMMM yyyy"
        )
        self.date.setMinimumHeight(46)

        time_col = QVBoxLayout()
        time_col.addWidget(
            QLabel(self._t("time"))
        )

        self.time = QTimeEdit()
        self.time.setObjectName("TimeInput")
        self.time.setDisplayFormat("HH:mm")
        self.time.setMinimumHeight(46)

        run_at = group.get("next_run")

        if not isinstance(
            run_at,
            dt.datetime,
        ):
            run_at = (
                dt.datetime.now()
                + dt.timedelta(minutes=10)
            )

        self.date.setDate(
            QDate(
                run_at.year,
                run_at.month,
                run_at.day,
            )
        )

        self.time.setTime(
            QTime(
                run_at.hour,
                run_at.minute,
            )
        )

        date_col.addWidget(self.date)
        time_col.addWidget(self.time)

        datetime_row.addLayout(
            date_col,
            1,
        )
        datetime_row.addLayout(
            time_col,
            1,
        )

        layout.addLayout(datetime_row)

        option_row = QHBoxLayout()

        repeat_col = QVBoxLayout()
        repeat_col.addWidget(
            QLabel(self._t("repeat"))
        )

        self.repeat = QComboBox()
        self.repeat.setObjectName(
            "ComboInput"
        )
        self.repeat.setMinimumHeight(44)
        for repeat_value in base.REPEAT_KEY_BY_VALUE:
            self.repeat.addItem(
                base.localized_repeat(
                    repeat_value,
                    self.language,
                ),
                repeat_value,
            )

        self.repeat.setCurrentIndex(
            max(
                0,
                self.repeat.findData(
                    str(
                        group.get("repeat")
                        or "once"
                    )
                ),
            )
        )

        repeat_col.addWidget(self.repeat)

        category_col = QVBoxLayout()
        category_col.addWidget(
            QLabel(self._t("category"))
        )

        self.category = QComboBox()
        self.category.setObjectName(
            "ComboInput"
        )
        self.category.setMinimumHeight(44)
        for category_value in core.CATEGORIES:
            self.category.addItem(
                base.localized_category(
                    category_value,
                    self.language,
                ),
                category_value,
            )
        self.category.setCurrentIndex(
            max(
                0,
                self.category.findData(
                    str(
                        group.get("category")
                        or "Genel"
                    )
                ),
            )
        )

        category_col.addWidget(
            self.category
        )

        option_row.addLayout(
            repeat_col,
            1,
        )
        option_row.addLayout(
            category_col,
            1,
        )

        layout.addLayout(option_row)

        layout.addWidget(
            QLabel(self._t("reminder_method"))
        )

        self.channel = QComboBox()
        self.channel.setObjectName(
            "ComboInput"
        )
        self.channel.setMinimumHeight(44)

        for channel_value in (
            "email",
            "pc",
            "both",
        ):
            self.channel.addItem(
                channel_label(
                    channel_value,
                    self.language,
                ),
                channel_value,
            )

        self.channel.setCurrentIndex(
            max(
                0,
                self.channel.findData(
                    str(
                        group.get("channel")
                        or "email"
                    )
                ),
            )
        )

        layout.addWidget(self.channel)

        layout.addWidget(
            QLabel(self._t("note"))
        )

        self.body = QTextEdit()
        self.body.setObjectName("NoteInput")
        self.body.setMinimumHeight(100)
        self.body.setText(
            str(
                group.get("body")
                or ""
            )
        )

        layout.addWidget(self.body)

        buttons = QHBoxLayout()

        cancel = QPushButton(
            self._t("cancel")
        )
        cancel.setObjectName(
            "SecondaryButton"
        )

        save = QPushButton(
            "✓  " + self._t("save_changes")
        )
        save.setObjectName(
            "SaveButton"
        )
        save.setMinimumHeight(46)

        cancel.clicked.connect(
            self.reject
        )
        save.clicked.connect(
            self.accept
        )

        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout.addLayout(buttons)

    def values(self):
        qdate = self.date.date()
        qtime = self.time.time()

        return {
            "subject":
                self.subject.text().strip(),
            "body":
                self.body.toPlainText().strip(),
            "run_at": dt.datetime(
                qdate.year(),
                qdate.month(),
                qdate.day(),
                qtime.hour(),
                qtime.minute(),
            ),
            "repeat":
                str(
                    self.repeat.currentData()
                    or "once"
                ),
            "channel": str(
                self.channel.currentData()
                or "email"
            ),
            "category":
                str(
                    self.category.currentData()
                    or "Genel"
                ),
        }


class UltimateReminderCard(QFrame):
    def __init__(
        self,
        group: Dict[str, object],
        owner,
    ):
        super().__init__()
        self.language = getattr(
            owner,
            "language",
            base.runtime_language(),
        )

        self.setObjectName("ReminderCard")
        self.setMinimumHeight(196)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            16,
            14,
            14,
            14,
        )
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(14)

        channel = str(
            group.get("channel")
            or "email"
        )

        icon = QLabel()
        icon.setObjectName(
            "ReminderIcon"
        )
        icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        icon.setFixedSize(58, 58)
        icon.setPixmap(
            base.make_line_icon(
                channel_icon(channel),
                "#27D3D1",
                25,
            ).pixmap(25, 25)
        )

        middle = QVBoxLayout()
        middle.setSpacing(4)

        run_at = group.get("next_run")

        when = (
            base.format_datetime(
                run_at,
                self.language,
            )
            if isinstance(
                run_at,
                dt.datetime,
            )
            else base.ui_text(
                "no_schedule",
                self.language,
            )
        )

        time = QLabel(when)
        time.setObjectName(
            "ReminderTime"
        )

        subject = QLabel(
            str(
                group.get("subject")
                or base.ui_text(
                    "untitled_reminder",
                    self.language,
                )
            )
        )
        subject.setObjectName(
            "ReminderSubject"
        )
        subject.setWordWrap(True)

        tags = QHBoxLayout()
        tags.setSpacing(6)

        for text, object_name in (
            (
                channel_label(
                    channel,
                    self.language,
                ),
                "ChannelTag",
            ),
            (
                base.localized_category(
                    str(
                        group.get("category")
                        or "Genel"
                    ),
                    self.language,
                ),
                "SecondaryTag",
            ),
            (
                base.localized_repeat(
                    str(
                        group.get("repeat")
                        or "once"
                    ),
                    self.language,
                ),
                "SecondaryTag",
            ),
            (
                base.ui_text(
                    "state_active",
                    self.language,
                )
                if bool(group.get("enabled"))
                else base.ui_text(
                    "state_paused",
                    self.language,
                ),
                "StateTagActive"
                if bool(group.get("enabled"))
                else "StateTagPaused",
            ),
        ):
            tag = QLabel(text)
            tag.setObjectName(
                object_name
            )
            tags.addWidget(tag)

        tags.addStretch(1)

        middle.addWidget(time)
        middle.addWidget(subject)
        middle.addLayout(tags)

        actions = QVBoxLayout()
        actions.setSpacing(4)

        first = QHBoxLayout()
        second = QHBoxLayout()

        edit = QPushButton(
            base.ui_text(
                "edit",
                self.language,
            )
        )
        pause = QPushButton(
            base.ui_text(
                "pause",
                self.language,
            )
            if bool(group.get("enabled"))
            else base.ui_text(
                "enable",
                self.language,
            )
        )

        duplicate = QPushButton(
            base.ui_text(
                "duplicate",
                self.language,
            )
        )
        snooze = QPushButton(
            base.ui_text(
                "snooze_ten",
                self.language,
            )
        )
        complete = QPushButton(
            base.ui_text(
                "complete",
                self.language,
            )
        )
        delete = QPushButton(
            base.ui_text(
                "delete",
                self.language,
            )
        )

        for button in (
            edit,
            pause,
            duplicate,
            snooze,
            complete,
        ):
            button.setObjectName(
                "SecondaryButton"
            )

        delete.setObjectName(
            "DangerButton"
        )

        edit.clicked.connect(
            lambda:
            owner._edit_group(group)
        )

        pause.clicked.connect(
            lambda:
            owner._toggle_group(group)
        )

        duplicate.clicked.connect(
            lambda:
            owner._duplicate_group(group)
        )

        snooze.clicked.connect(
            lambda:
            owner._snooze_group(group)
        )

        complete.clicked.connect(
            lambda:
            owner._complete_group(group)
        )

        delete.clicked.connect(
            lambda:
            owner._delete_group(group)
        )

        first.addWidget(edit)
        first.addWidget(pause)
        first.addWidget(duplicate)

        second.addWidget(snooze)
        second.addWidget(complete)
        second.addWidget(delete)

        actions.addLayout(first)
        actions.addLayout(second)

        top.addWidget(icon)
        top.addLayout(middle, 1)
        layout.addLayout(top)
        layout.addLayout(actions)


class UltimateWindow(FinalWindow):
    def __init__(self):
        self.tray = None
        self.quick_input = None

        super().__init__()

        self.apply_ultimate_styles()
        self.setup_tray()

    def apply_ultimate_styles(self):
        self.setStyleSheet(
            self.styleSheet()
            + """
            QFrame#QuickBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D1A23,
                    stop:1 #0A151D
                );
                border: 1px solid #2B4652;
                border-radius: 13px;
            }

            QLabel#QuickTitle {
                color: #EAF4F7;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#QuickHint {
                color: #778A96;
                font-size: 11px;
            }

            QPushButton#QuickChip {
                background: #0B161F;
                border: 1px solid #2D4551;
                color: #9DB0BA;
                border-radius: 7px;
                padding: 7px 10px;
                font-size: 11px;
            }

            QPushButton#QuickChip:hover {
                border-color: #23828B;
                color: #E9FCFC;
                background: #10232B;
            }

            QCheckBox {
                color: #C1CDD4;
                spacing: 8px;
                font-size: 12px;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }

            QMenu {
                background: #0C151D;
                color: #DDE8ED;
                border: 1px solid #2A3E49;
                padding: 7px;
            }

            QMenu::item {
                padding: 8px 28px 8px 12px;
                border-radius: 5px;
            }

            QMenu::item:selected {
                background: #12313A;
                color: #43E2DD;
            }
            """
        )

    def build_main(self):
        main = super().build_main()

        quick = self.build_quick_bar()

        layout = main.layout()

        if layout is not None:
            layout.insertWidget(
                1,
                quick,
            )

        return main

    def build_quick_bar(self):
        bar = QFrame()
        bar.setObjectName("QuickBar")

        layout = QVBoxLayout(bar)
        layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )
        layout.setSpacing(7)

        top = QHBoxLayout()

        title = QLabel(
            "⚡ " + self._t("quick_title")
        )
        title.setObjectName(
            "QuickTitle"
        )

        hint = QLabel(
            self._t("quick_hint")
        )
        hint.setObjectName(
            "QuickHint"
        )

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(hint)

        layout.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.quick_input = QLineEdit()
        self.quick_input.setObjectName(
            "TextInput"
        )
        self.quick_input.setMinimumHeight(42)
        self.quick_input.setPlaceholderText(
            self._t("quick_placeholder")
        )

        apply_button = QPushButton(
            self._t("quick_apply")
        )
        apply_button.setObjectName(
            "SecondaryButton"
        )

        quick_save = QPushButton(
            self._t("quick_save")
        )
        quick_save.setObjectName(
            "SaveButton"
        )
        quick_save.setMinimumHeight(42)

        row.addWidget(
            self.quick_input,
            1,
        )
        row.addWidget(apply_button)
        row.addWidget(quick_save)

        layout.addLayout(row)

        chips = QHBoxLayout()
        chips.setSpacing(6)

        for text, minutes in (
            (
                self._t(
                    "quick_plus_minutes",
                    minutes=30,
                ),
                30,
            ),
            (
                self._t(
                    "quick_plus_hours",
                    hours=1,
                ),
                60,
            ),
            (
                self._t(
                    "quick_plus_hours",
                    hours=2,
                ),
                120,
            ),
        ):
            button = QPushButton(text)
            button.setObjectName(
                "QuickChip"
            )

            button.clicked.connect(
                lambda _=False, m=minutes:
                self._set_relative_time(m)
            )

            chips.addWidget(button)

        tomorrow = QPushButton(
            self._t("quick_tomorrow")
        )
        tomorrow.setObjectName(
            "QuickChip"
        )
        tomorrow.clicked.connect(
            self._set_tomorrow_morning
        )

        chips.addWidget(tomorrow)
        chips.addStretch(1)

        layout.addLayout(chips)

        apply_button.clicked.connect(
            self.quick_to_form
        )

        quick_save.clicked.connect(
            self.quick_save
        )

        self.quick_input.returnPressed.connect(
            self.quick_to_form
        )

        return bar

    def build_form_card(self):
        card = super().build_form_card()

        layout = card.layout()

        self.category_combo = QComboBox()
        self.category_combo.setObjectName(
            "ComboInput"
        )
        self.category_combo.setMinimumHeight(46)
        for category_value in core.CATEGORIES:
            self.category_combo.addItem(
                base.localized_category(
                    category_value,
                    self.language,
                ),
                category_value,
            )

        self.category_combo.setCurrentIndex(
            max(
                0,
                self.category_combo.findData(
                    str(
                        self.final_settings.get(
                            "default_category",
                            "Genel",
                        )
                    )
                ),
            )
        )

        category_label = QLabel(
            self._t("category")
        )
        category_label.setObjectName(
            "FieldLabel"
        )

        insert_at = (
            layout.count() - 4
            if layout is not None
            else 0
        )

        if layout is not None:
            # "Not" alanından hemen önce.
            for index in range(
                layout.count()
            ):
                item = layout.itemAt(index)
                widget = item.widget()

                if (
                    isinstance(widget, QLabel)
                    and widget.property(
                        "fieldRole"
                    ) == "note"
                ):
                    insert_at = index
                    break

            layout.insertWidget(
                insert_at,
                category_label,
            )

            layout.insertWidget(
                insert_at + 1,
                self.category_combo,
            )

        return card

    def _set_relative_time(
        self,
        minutes: int,
    ):
        target = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(
                minutes=minutes
            )
        )

        self.date_edit.setDate(
            QDate(
                target.year,
                target.month,
                target.day,
            )
        )

        self.time_edit.setTime(
            QTime(
                target.hour,
                target.minute,
            )
        )

        self.subject_edit.setFocus()

    def _set_tomorrow_morning(self):
        target = (
            dt.datetime.now()
            + dt.timedelta(days=1)
        ).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )

        self.date_edit.setDate(
            QDate(
                target.year,
                target.month,
                target.day,
            )
        )

        self.time_edit.setTime(
            QTime(9, 0)
        )

        self.subject_edit.setFocus()

    def quick_to_form(self):
        text = (
            self.quick_input.text().strip()
            if self.quick_input
            else ""
        )

        try:
            result = parse_quick(text)
        except (ValueError, OverflowError):
            result = None

        if result is None:
            self.show_status(
                self._t("quick_parse_failed")
            )
            return

        self.subject_edit.setText(
            result.subject
        )

        self.date_edit.setDate(
            QDate(
                result.run_at.year,
                result.run_at.month,
                result.run_at.day,
            )
        )

        self.time_edit.setTime(
            QTime(
                result.run_at.hour,
                result.run_at.minute,
            )
        )

        self.repeat_combo.setCurrentIndex(
            max(
                0,
                self.repeat_combo.findData(
                    result.repeat
                ),
            )
        )

        self.show_status(
            "✓ " + self._t("quick_parsed")
        )

    def quick_save(self):
        text = (
            self.quick_input.text().strip()
            if self.quick_input
            else ""
        )

        try:
            result = parse_quick(text)
        except (ValueError, OverflowError):
            result = None

        if result is None:
            self.show_status(
                self._t("quick_parse_failed")
            )
            return

        try:
            core.save_group(
                pair_id=None,
                channel=str(
                    self.final_settings.get(
                        "default_channel",
                        self.default_channel,
                    )
                ),
                subject=result.subject,
                body=result.subject,
                run_at=result.run_at,
                repeat=result.repeat,
                category=str(
                    self.final_settings.get(
                        "default_category",
                        "Genel",
                    )
                ),
            )
        except Exception as exc:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page("today")

        self.show_status(
            "✓ " + self._t("quick_saved")
        )

    def preview_save(self):
        subject = (
            self.subject_edit
            .text()
            .strip()
        )

        if not subject:
            self.show_status(
                self._t("title_required")
            )
            return

        qdate = self.date_edit.date()
        qtime = self.time_edit.time()

        run_at = dt.datetime(
            qdate.year(),
            qdate.month(),
            qdate.day(),
            qtime.hour(),
            qtime.minute(),
        )

        repeat = self.repeat_combo.currentData()

        if repeat is None:
            self.show_status(
                self._t("invalid_repeat")
            )
            return

        channel = {
            0: "email",
            1: "pc",
            2: "both",
        }.get(
            self.delivery_group.checkedId(),
            "email",
        )

        try:
            core.save_group(
                pair_id=None,
                channel=channel,
                subject=subject,
                body=(
                    self.note_edit
                    .toPlainText()
                    .strip()
                ),
                run_at=run_at,
                repeat=repeat,
                category=(
                    str(
                        self.category_combo
                        .currentData()
                        or "Genel"
                    )
                ),
            )

        except Exception as exc:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page("today")

        self.show_status(
            "✓ "
            + self._t(
                "reminder_saved",
                channel=channel_label(
                    channel,
                    self.language,
                ),
            )
        )

    def focus_quick_input(self):
        if self.current_page != "today":
            self.switch_page("today")

        QTimer.singleShot(
            80,
            lambda:
            self.quick_input.setFocus()
            if self.quick_input
            else None,
        )

    def build_reminders_page(self):
        page, layout = self._page_shell(
            self._t("nav_reminders"),
            self._t("reminders_subtitle"),
        )

        controls = QHBoxLayout()
        controls.setSpacing(8)

        search = QLineEdit()
        search.setObjectName("TextInput")
        search.setPlaceholderText(
            self._t("search_reminders")
        )
        search.setMinimumHeight(42)

        channel = QComboBox()
        channel.setObjectName("ComboInput")
        channel.addItem(
            self._t("all_channels"),
            "all",
        )
        for channel_value in (
            "email",
            "pc",
            "both",
        ):
            channel.addItem(
                channel_label(
                    channel_value,
                    self.language,
                ),
                channel_value,
            )

        category = QComboBox()
        category.setObjectName("ComboInput")
        category.addItem(
            self._t("all_categories"),
            "all",
        )
        for category_value in core.CATEGORIES:
            category.addItem(
                base.localized_category(
                    category_value,
                    self.language,
                ),
                category_value,
            )

        state = QComboBox()
        state.setObjectName("ComboInput")
        state.addItem(
            self._t("all_states"),
            "all",
        )
        state.addItem(
            self._t("state_active"),
            "active",
        )
        state.addItem(
            self._t("state_paused"),
            "paused",
        )

        for combo in (
            channel,
            category,
            state,
        ):
            combo.setMinimumHeight(42)

        controls.addWidget(search, 1)
        controls.addWidget(channel)
        controls.addWidget(category)
        controls.addWidget(state)

        layout.addLayout(controls)

        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        cards = QVBoxLayout(container)
        cards.setContentsMargins(
            0,
            5,
            0,
            5,
        )
        cards.setSpacing(10)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.preview_status = QLabel("")
        self.preview_status.setObjectName(
            "PreviewStatus"
        )
        self.preview_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.preview_status
        )

        def clear_cards():
            while cards.count():
                item = cards.takeAt(0)

                if item.widget():
                    item.widget().deleteLater()

        def render():
            clear_cards()

            channel_value = str(
                channel.currentData()
                or "all"
            )

            category_value = str(
                category.currentData()
                or "all"
            )

            groups = core.search_groups(
                search.text(),
                channel=channel_value,
                category=category_value,
                include_disabled=True,
            )

            if state.currentData() == "active":
                groups = [
                    g
                    for g in groups
                    if bool(g.get("enabled"))
                ]

            elif (
                state.currentData()
                == "paused"
            ):
                groups = [
                    g
                    for g in groups
                    if not bool(
                        g.get("enabled")
                    )
                ]

            if not groups:
                empty = QLabel(
                    self._t("no_filter_match")
                )
                empty.setObjectName("PageSub")
                empty.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                cards.addWidget(empty)

            for group in groups:
                cards.addWidget(
                    UltimateReminderCard(
                        group,
                        self,
                    )
                )

            cards.addStretch(1)

        search.textChanged.connect(
            lambda _:
            render()
        )

        channel.currentTextChanged.connect(
            lambda _:
            render()
        )

        category.currentTextChanged.connect(
            lambda _:
            render()
        )

        state.currentTextChanged.connect(
            lambda _:
            render()
        )

        render()

        return page

    def _edit_group(self, group):
        dialog = UltimateEditDialog(
            self,
            group,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        values = dialog.values()

        try:
            core.save_group(
                pair_id=str(
                    group["pair_id"]
                ),
                **values,
            )

        except Exception as exc:
            self.show_status(
                self._t(
                    "update_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ " + self._t("reminder_updated")
        )

    def _duplicate_group(self, group):
        try:
            core.duplicate_group(
                str(
                    group["pair_id"]
                )
            )
        except Exception as exc:
            self.show_status(
                self._t(
                    "duplicate_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ "
            + self._t("reminder_duplicated")
        )

    def _snooze_group(self, group):
        settings = core.load_settings()

        minutes = int(
            settings.get(
                "default_snooze_minutes",
                10,
            )
        )

        try:
            core.snooze_group(
                str(group["pair_id"]),
                minutes,
            )
        except Exception as exc:
            self.show_status(
                self._t(
                    "snooze_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ "
            + self._t(
                "reminder_snoozed",
                minutes=minutes,
            )
        )

    def _complete_group(self, group):
        try:
            core.complete_group(
                str(group["pair_id"])
            )
        except Exception as exc:
            self.show_status(
                self._t(
                    "complete_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ "
            + self._t("reminder_completed")
        )

    def _delete_group(self, group):
        dialog = PremiumConfirmDialog(
            self,
            self._t("delete_reminder"),
            self._t(
                "delete_confirm",
                subject=str(
                    group.get("subject")
                    or self._t("untitled_reminder")
                ),
            ),
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        try:
            core.delete_group(
                str(group["pair_id"])
            )
        except Exception as exc:
            self.show_status(
                self._t(
                    "delete_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ " + self._t("reminder_deleted")
        )

    def build_settings_page(self):
        page = super().build_settings_page()

        layout = page.layout()

        if layout is None:
            return page

        settings = core.load_settings()

        quiet_card, quiet_layout = (
            self._setting_card(
                self._t("quiet_hours_title"),
                self._t("quiet_hours_detail"),
            )
        )

        enabled = QCheckBox(
            self._t("enabled")
        )
        enabled.setChecked(
            bool(
                settings.get(
                    "quiet_hours_enabled",
                    False,
                )
            )
        )

        start = QTimeEdit()
        start.setObjectName("TimeInput")
        start.setDisplayFormat("HH:mm")

        end = QTimeEdit()
        end.setObjectName("TimeInput")
        end.setDisplayFormat("HH:mm")

        def parse_clock(value):
            try:
                h, m = map(
                    int,
                    str(value).split(":"),
                )
                return QTime(h, m)
            except Exception:
                return QTime(22, 0)

        start.setTime(
            parse_clock(
                settings.get(
                    "quiet_hours_start",
                    "22:00",
                )
            )
        )

        end.setTime(
            parse_clock(
                settings.get(
                    "quiet_hours_end",
                    "08:00",
                )
            )
        )

        save = QPushButton(
            self._t("save")
        )
        save.setObjectName(
            "SecondaryButton"
        )

        def save_quiet():
            core.save_settings(
                {
                    "quiet_hours_enabled":
                        enabled.isChecked(),
                    "quiet_hours_start":
                        start.time().toString(
                            "HH:mm"
                        ),
                    "quiet_hours_end":
                        end.time().toString(
                            "HH:mm"
                        ),
                }
            )

            self.final_settings = (
                core.load_settings()
            )

            self.show_status(
                "✓ "
                + self._t(
                    "quiet_hours_saved"
                )
            )

        save.clicked.connect(
            save_quiet
        )

        quiet_layout.addWidget(enabled)
        quiet_layout.addWidget(start)
        quiet_layout.addWidget(end)
        quiet_layout.addWidget(save)

        category_card, category_layout = (
            self._setting_card(
                self._t("default_category_title"),
                self._t("default_category_detail"),
            )
        )

        default_category = QComboBox()
        default_category.setObjectName(
            "ComboInput"
        )
        for category_value in core.CATEGORIES:
            default_category.addItem(
                base.localized_category(
                    category_value,
                    self.language,
                ),
                category_value,
            )

        default_category.setCurrentIndex(
            max(
                0,
                default_category.findData(
                    str(
                        settings.get(
                            "default_category",
                            "Genel",
                        )
                    )
                ),
            )
        )

        category_save = QPushButton(
            self._t("save")
        )
        category_save.setObjectName(
            "SecondaryButton"
        )

        def save_category():
            core.save_settings(
                {
                    "default_category":
                        str(
                            default_category
                            .currentData()
                            or "Genel"
                        )
                }
            )

            self.final_settings = (
                core.load_settings()
            )

            self.show_status(
                "✓ "
                + self._t(
                    "default_category_saved"
                )
            )

        category_save.clicked.connect(
            save_category
        )

        category_layout.addWidget(
            default_category
        )
        category_layout.addWidget(
            category_save
        )

        # PreviewStatus'tan ve stretch'ten önce ekle.
        insert_at = max(
            2,
            layout.count() - 2,
        )

        layout.insertWidget(
            insert_at,
            quiet_card,
        )

        layout.insertWidget(
            insert_at + 1,
            category_card,
        )

        return page

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QSystemTrayIcon(
            QIcon(str(ICON_PATH)),
            self,
        )

        self.tray.setToolTip(
            self._t("app_name")
        )

        menu = QMenu()
        menu.setStyleSheet(
            self.styleSheet()
        )

        open_action = QAction(
            self._t("tray_open"),
            self,
        )

        quick_action = QAction(
            self._t("tray_quick"),
            self,
        )

        today_action = QAction(
            self._t("nav_today"),
            self,
        )

        reminders_action = QAction(
            self._t("nav_reminders"),
            self,
        )

        settings_action = QAction(
            self._t("nav_settings"),
            self,
        )

        quit_action = QAction(
            self._t("quit"),
            self,
        )

        open_action.triggered.connect(
            self._raise_window
        )

        quick_action.triggered.connect(
            self.focus_quick_input
        )

        today_action.triggered.connect(
            lambda:
            self._show_page("today")
        )

        reminders_action.triggered.connect(
            lambda:
            self._show_page(
                "reminders"
            )
        )

        settings_action.triggered.connect(
            lambda:
            self._show_page("settings")
        )

        quit_action.triggered.connect(
            QApplication.instance().quit
        )

        menu.addAction(open_action)
        menu.addAction(quick_action)
        menu.addSeparator()
        menu.addAction(today_action)
        menu.addAction(reminders_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

        self.tray.activated.connect(
            lambda reason:
            self._raise_window()
            if reason
            == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )

        self.tray.show()

    def _raise_window(self):
        if self.isMinimized():
            self.showNormal()

        self.show()
        self.raise_()
        self.activateWindow()

    def _show_page(self, page):
        self._raise_window()
        self.switch_page(page)



class ResponsiveUltimateWindow(UltimateWindow):
    """
    Final responsive desktop layer.

    Principle:
    Never compress form controls until labels collide.
    On shorter windows the page becomes vertically scrollable.
    """

    def __init__(self):
        super().__init__()

        # Küçük laptop penceresinde de kullanılabilir,
        # fakat içerik sıkıştırılmak yerine scroll edilir.
        self.setMinimumSize(
            960,
            680,
        )

        self._apply_responsive_styles()

    def _apply_responsive_styles(self):
        self.setStyleSheet(
            self.styleSheet()
            + """
            QScrollArea#ResponsivePageScroll {
                background: transparent;
                border: none;
            }

            QScrollArea#ResponsivePageScroll
            > QWidget
            > QWidget {
                background: transparent;
            }

            QScrollBar:vertical {
                background: #08121A;
                width: 9px;
                margin: 4px 1px 4px 1px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #24424D;
                min-height: 42px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #25808A;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
                height: 0px;
            }

            QPushButton#SecondaryButton {
                min-height: 28px;
                padding-left: 10px;
                padding-right: 10px;
            }

            QPushButton#DangerButton {
                min-height: 28px;
                padding-left: 10px;
                padding-right: 10px;
            }

            QLabel#PageTitle {
                margin-bottom: 2px;
            }
            """
        )

    def _responsive_shell(
        self,
        content: QWidget,
        *,
        minimum_content_height: int,
    ) -> QFrame:
        # Kritik nokta:
        # İç sayfa bu yüksekliğin altına ezilmez.
        content.setMinimumHeight(
            minimum_content_height
        )

        scroll = QScrollArea()
        scroll.setObjectName(
            "ResponsivePageScroll"
        )

        scroll.setWidgetResizable(True)

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setWidget(content)

        shell = QFrame()
        shell.setObjectName("Main")

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(0)

        layout.addWidget(scroll)

        return shell

    def build_main(self):
        content = super().build_main()
        self._dashboard_content = content

        # Tam ekran görünümünü bozmaz.
        # Küçük yükseklikte form artık asla üst üste binmez.
        shell = self._responsive_shell(
            content,
            minimum_content_height=820,
        )
        self._update_dashboard_composition(
            self.width()
        )
        return shell

    def _update_dashboard_composition(
        self,
        width: int,
    ) -> None:
        # Dashboard layout references belong only to the live Today page.
        # Other pages can outlive the old dashboard Python wrappers until
        # Qt drains DeferredDelete events, so never dereference them there.
        if getattr(self, "current_page", "today") != "today":
            return

        columns = getattr(
            self,
            "dashboard_columns",
            None,
        )
        content = getattr(
            self,
            "_dashboard_content",
            None,
        )
        if columns is None or content is None:
            return

        # Two full reminder columns need roughly 1,010 logical pixels after
        # the sidebar and scroll-bar gutter.  Keep the cards stacked through
        # compact desktop widths so long translations cannot force even a
        # one-pixel horizontal scroll range at fractional scale factors.
        stacked = width < 1320
        columns.setDirection(
            QBoxLayout.Direction.TopToBottom
            if stacked
            else QBoxLayout.Direction.LeftToRight
        )
        content.setMinimumHeight(
            1660 if stacked else 820
        )

        info_layout = getattr(
            self,
            "info_strip_layout",
            None,
        )
        info_strip = getattr(
            self,
            "info_strip",
            None,
        )
        if info_layout is not None and info_strip is not None:
            info_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if stacked
                else QBoxLayout.Direction.LeftToRight
            )
            info_strip.setFixedHeight(
                278 if stacked else 116
            )

    def build_settings_page(self):
        content = super().build_settings_page()

        return self._responsive_shell(
            content,
            minimum_content_height=700,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if not hasattr(
            self,
            "sidebar",
        ):
            return

        width = self.width()

        # Adaptif sidebar.
        if width < 1180:
            sidebar_width = 245

        elif width < 1320:
            sidebar_width = 250

        else:
            sidebar_width = 270

        if (
            self.sidebar.width()
            != sidebar_width
        ):
            self.sidebar.setFixedWidth(
                sidebar_width
            )

        self._update_dashboard_composition(
            width
        )



class FinalPolishWindow(ResponsiveUltimateWindow):
    VERSION = app_identity.APP_VERSION

    def __init__(self):
        self._force_quit = False
        self._tray_hint_shown = False
        self.language_button = None

        super().__init__()

        self._apply_final_polish()
        self._rebuild_final_tray()

    def switch_page(self, page_id: str) -> None:
        previous_page = getattr(self, "current_page", "today")
        super().switch_page(page_id)
        if previous_page == "settings" and page_id != "settings":
            # Do not retain a wrapper for the retired Settings page.  Qt
            # owns the live selector through its parent/layout hierarchy.
            self.language_button = None

    def _apply_final_polish(self):
        self.setStyleSheet(
            self.styleSheet()
            + """
            QPushButton#SecondaryButton {
                min-height: 31px;
                min-width: 76px;
                padding: 2px 12px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 7px;
            }

            QToolButton#languageSelector {
                min-height: 36px;
                padding: 2px 30px 2px 12px;
                color: #DDE8ED;
                background: #0B151D;
                border: 1px solid #36505D;
                border-radius: 7px;
                font-size: 12px;
                font-weight: 650;
                text-align: left;
            }

            QToolButton#languageSelector:hover,
            QToolButton#languageSelector:focus {
                border-color: #2CBFC0;
                color: #F3FFFF;
                background: #10242B;
            }

            QToolButton#languageSelector::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 10px;
            }

            QPushButton#DangerButton {
                min-height: 31px;
                min-width: 58px;
                padding: 2px 11px;
                font-size: 12px;
                font-weight: 650;
                border-radius: 7px;
            }

            QComboBox#ComboInput {
                min-height: 36px;
                padding-left: 11px;
                padding-right: 10px;
            }

            QTimeEdit#TimeInput,
            QDateEdit#DateInput {
                min-height: 36px;
            }

            QFrame#SettingCard {
                min-height: 64px;
            }

            QFrame#ReminderCard {
                margin-top: 2px;
                margin-bottom: 2px;
            }

            QLabel#SettingTitle {
                font-size: 13px;
                font-weight: 750;
            }

            QLabel#SettingDetail {
                font-size: 12px;
                line-height: 1.3;
            }
            """
        )

    def _quit_application(self):
        self._force_quit = True

        if self.tray is not None:
            self.tray.hide()

        app = QApplication.instance()

        if app is not None:
            app.quit()

    def _rebuild_final_tray(self):
        if self.tray is None:
            return

        menu = QMenu()
        menu.setStyleSheet(
            self.styleSheet()
        )

        open_action = QAction(
            self._t("tray_open"),
            self,
        )

        quick_action = QAction(
            "＋  " + self._t("tray_quick"),
            self,
        )

        today_action = QAction(
            self._t("nav_today"),
            self,
        )

        reminders_action = QAction(
            self._t("nav_reminders"),
            self,
        )

        history_action = QAction(
            self._t("nav_history"),
            self,
        )

        settings_action = QAction(
            self._t("nav_settings"),
            self,
        )

        quit_action = QAction(
            self._t("quit"),
            self,
        )

        open_action.triggered.connect(
            self._raise_window
        )

        quick_action.triggered.connect(
            self.focus_quick_input
        )

        today_action.triggered.connect(
            lambda:
            self._show_page("today")
        )

        reminders_action.triggered.connect(
            lambda:
            self._show_page(
                "reminders"
            )
        )

        history_action.triggered.connect(
            lambda:
            self._show_page("history")
        )

        settings_action.triggered.connect(
            lambda:
            self._show_page("settings")
        )

        quit_action.triggered.connect(
            self._quit_application
        )

        menu.addAction(open_action)
        menu.addAction(quick_action)

        menu.addSeparator()

        menu.addAction(today_action)
        menu.addAction(reminders_action)
        menu.addAction(history_action)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action.setIcon(
            base.make_line_icon(
                "local",
                "#D97B84",
                18,
            )
        )

        menu.addAction(quit_action)

        self._final_tray_menu = menu

        self.tray.setContextMenu(
            menu
        )

        # Replace previous one-way tray activation.
        try:
            self.tray.activated.disconnect()
        except (TypeError, RuntimeError):
            pass

        self.tray.activated.connect(
            self._on_final_tray_activated
        )

    def _on_final_tray_activated(
        self,
        reason,
    ):
        if (
            reason
            != QSystemTrayIcon
            .ActivationReason
            .Trigger
        ):
            return

        if (
            self.isVisible()
            and not self.isMinimized()
        ):
            self.hide()
            return

        self._raise_window()

    def _open_external_url(
        self,
        url: str,
    ) -> None:
        try:
            opened = QDesktopServices.openUrl(
                QUrl(url)
            )
        except Exception:
            opened = False

        if not opened:
            self.show_status(
                self._t(
                    "external_link_failed"
                )
            )

    def _change_language(
        self,
        language: str,
    ) -> None:
        normalized = l10n.normalize_language(
            language
        )
        if normalized == self.language:
            return

        settings = runtime_config.load_settings()
        settings["language"] = normalized
        try:
            runtime_config.save_settings(
                settings
            )
        except OSError:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t(
                        "operation_failed_detail"
                    ),
                )
            )
            return

        current_page = self.current_page
        self.runtime_settings = settings
        self.language = normalized
        if not str(
            settings.get(
                "profile_name",
                "",
            )
            or ""
        ).strip():
            self.profile_name = self._t(
                "default_profile_name"
            )

        old_sidebar = self.sidebar
        self.nav_buttons = []
        new_sidebar = self.build_sidebar()
        if self.width() < 1180:
            new_sidebar.setFixedWidth(245)
        elif self.width() < 1320:
            new_sidebar.setFixedWidth(250)
        else:
            new_sidebar.setFixedWidth(270)
        self.body_layout.replaceWidget(
            old_sidebar,
            new_sidebar,
        )
        old_sidebar.hide()
        old_sidebar.deleteLater()
        self.sidebar = new_sidebar

        self.setWindowTitle(
            self._t("app_name")
        )
        app = QApplication.instance()
        if app is not None:
            app.setApplicationDisplayName(
                self._t("app_name")
            )

        self.switch_page(current_page)
        self._rebuild_final_tray()
        self._update_dashboard_composition(
            self.width()
        )
        self.show_status(
            self._t("language_changed")
        )

    def build_settings_page(self):
        shell = super().build_settings_page()

        scroll = shell.findChild(
            QScrollArea,
            "ResponsivePageScroll",
        )

        if scroll is None:
            return shell

        content = scroll.widget()

        if content is None:
            return shell

        layout = content.layout()

        if layout is None:
            return shell

        settings = core.load_settings()

        language_card, language_layout = (
            self._setting_card(
                self._t(
                    "settings_language_title"
                ),
                self._t(
                    "settings_language_detail"
                ),
            )
        )
        self.language_button = LanguageMenuButton(
            self,
            language=self.language,
        )
        self.language_button.setMinimumWidth(180)
        self.language_button.setAccessibleName(
            self._t(
                "settings_language_title"
            )
        )
        self.language_button.setAccessibleDescription(
            self._t(
                "settings_language_detail"
            )
        )
        self.language_button.setToolTip(
            self._t(
                "settings_language_detail"
            )
        )
        self.language_button.languageChanged.connect(
            self._change_language
        )
        language_layout.addWidget(
            self.language_button
        )
        layout.insertWidget(
            1,
            language_card,
        )

        tray_card, tray_layout = (
            self._setting_card(
                self._t("tray_behavior_title"),
                self._t("tray_behavior_detail"),
            )
        )

        enabled = QCheckBox(
            self._t("enabled")
        )

        enabled.setChecked(
            bool(
                settings.get(
                    "minimize_to_tray",
                    True,
                )
            )
        )

        save = QPushButton(
            self._t("save")
        )
        save.setObjectName(
            "SecondaryButton"
        )

        def persist():
            core.save_settings(
                {
                    "minimize_to_tray":
                        enabled.isChecked()
                }
            )

            self.final_settings = (
                core.load_settings()
            )

            self.show_status(
                "✓ "
                + self._t(
                    "tray_behavior_saved"
                )
            )

        save.clicked.connect(
            persist
        )

        tray_layout.addWidget(enabled)
        tray_layout.addWidget(save)

        diagnostic_card, diagnostic_layout = (
            self._setting_card(
                self._t("about_title"),
                self._t(
                    "about_detail",
                    version=app_identity.APP_VERSION,
                )
                + "\n"
                + self._t("support_detail"),
            )
        )

        badge = QLabel(self.VERSION)
        badge.setObjectName(
            "SystemLivePill"
        )

        link_panel = QWidget()
        link_panel.setMinimumWidth(205)
        link_layout = QVBoxLayout(link_panel)
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.setSpacing(7)
        link_layout.addWidget(
            badge,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        self.support_link_buttons = []
        for label_key, url in SUPPORT_LINKS:
            button = QPushButton(
                self._t(label_key)
            )
            button.setObjectName(
                "SecondaryButton"
            )
            button.setProperty(
                "support_key",
                label_key,
            )
            button.setProperty(
                "external_url",
                url,
            )
            button.clicked.connect(
                lambda checked=False, target=url:
                self._open_external_url(
                    target
                )
            )
            self.support_link_buttons.append(
                button
            )
            link_layout.addWidget(button)

        diagnostic_layout.addWidget(
            link_panel
        )

        insert_at = max(
            2,
            layout.count() - 2,
        )

        layout.insertWidget(
            insert_at,
            tray_card,
        )

        layout.insertWidget(
            insert_at + 1,
            diagnostic_card,
        )

        return shell

    def closeEvent(self, event):
        settings = core.load_settings()

        minimize = bool(
            settings.get(
                "minimize_to_tray",
                True,
            )
        )

        if (
            not self._force_quit
            and minimize
            and self.tray is not None
            and self.tray.isVisible()
        ):
            event.ignore()
            self.hide()

            if not self._tray_hint_shown:
                self._tray_hint_shown = True

                self.tray.showMessage(
                    self._t("app_name"),
                    self._t("tray_continues"),
                    QSystemTrayIcon.MessageIcon.Information,
                    4500,
                )

            return

        event.accept()


def _forward_to_existing_instance(
    server_name: str,
    command: bytes,
    *,
    timeout_ms: int = 350,
) -> bool:
    probe = QLocalSocket()
    probe.connectToServer(server_name)

    if not probe.waitForConnected(timeout_ms):
        return False

    probe.write(command)
    probe.flush()
    probe.waitForBytesWritten(timeout_ms)
    probe.disconnectFromServer()
    return True


def _forward_to_starting_instance(
    server_name: str,
    command: bytes,
) -> bool:
    """Give a lock-owning process a bounded interval to publish its socket."""
    for attempt in range(4):
        if _forward_to_existing_instance(
            server_name,
            command,
        ):
            return True
        if attempt < 3:
            time.sleep(
                0.05 * (attempt + 1)
            )
    return False


def acquire_single_instance(
    server_name: str,
    command: bytes,
) -> tuple[QLocalServer | None, bool]:
    """Atomically become the public instance or notify the live owner.

    The owner keeps the hardened filesystem lock for its full lifetime.  A
    stale local-socket endpoint is removed only after acquiring that lock,
    after listen failed, and after a second connection attempt also failed.
    This prevents a second launch from unlinking a starting, live, or briefly
    unresponsive owner's server.
    """
    lock_handle = try_acquire_owner_lock()

    if lock_handle is None:
        if _forward_to_starting_instance(
            server_name,
            command,
        ):
            return None, True

        # A lifetime lock proves that a cooperative owner is still starting
        # or temporarily unable to accept connections.  Fail closed and
        # never unlink its endpoint.
        return None, False

    try:
        server = QLocalServer()
        if server.listen(server_name):
            server._lifetime_lock_handle = lock_handle
            lock_handle = None
            return server, False

        if _forward_to_existing_instance(
            server_name,
            command,
        ):
            return None, True

        # Both a bind and a live connection failed while holding the
        # lifetime lock, so no cooperative owner can exist.  The endpoint
        # is stale and safe to remove.
        QLocalServer.removeServer(
            server_name
        )

        server = QLocalServer()
        if server.listen(server_name):
            server._lifetime_lock_handle = lock_handle
            lock_handle = None
            return server, False

        # A non-cooperating process may have appeared.  Never unlink it;
        # make one final forwarding attempt and otherwise fail closed.
        if _forward_to_existing_instance(
            server_name,
            command,
        ):
            return None, True

        return None, False
    finally:
        if lock_handle is not None:
            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_UN,
            )
            lock_handle.close()


def main():
    app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(False)

    app.setApplicationName(
        app_identity.APP_ID
    )

    app.setApplicationVersion(
        app_identity.APP_VERSION
    )

    app.setApplicationDisplayName(
        base.ui_text("app_name")
    )

    app.setDesktopFileName(
        app_identity.APP_ID
    )

    app.setOrganizationDomain(
        app_identity.ORGANIZATION_DOMAIN
    )

    app.setStyle("Fusion")

    app.setFont(
        QFont(
            base.select_font(),
            10,
        )
    )

    icon = QIcon(
        str(ICON_PATH)
    )

    app.setWindowIcon(icon)

    server_name = (
        app_identity.APP_ID
        .replace(".", "-")
        + "-"
        + str(os.getuid())
    )

    command = (
        b"quick"
        if "--quick" in sys.argv
        else b"raise"
    )

    server, forwarded = acquire_single_instance(
        server_name,
        command,
    )

    if forwarded:
        return 0

    if server is None:
        return 3

    window = FinalPolishWindow()
    window.setWindowIcon(icon)

    # HATIRLATICI_INTERNAL_SCHEDULER_V1
    scheduler = DeliveryScheduler(
        parent=window,
    )

    window._delivery_scheduler = (
        scheduler
    )

    def show_delivery_status(
        status: str,
    ) -> None:
        key = pc_delivery_status_key(
            status
        )
        if key is not None:
            window.show_status(
                window._t(key)
            )

    scheduler.statusChanged.connect(
        show_delivery_status
    )

    scheduler.start()

    app.aboutToQuit.connect(
        scheduler.stop
    )

    # HATIRLATICI_MAIL_SCHEDULER_V1
    mail_scheduler = MailDeliveryScheduler(
        parent=window,
    )

    window._mail_delivery_scheduler = (
        mail_scheduler
    )

    def show_mail_status(status: str) -> None:
        prefix = "smtp-error:"
        if not status.startswith(prefix):
            return

        code = status[len(prefix):].strip()
        supported = {
            "dns",
            "timeout",
            "tls",
            "auth",
            "invalid_sender",
            "recipient_refused",
            "offline",
            "generic",
        }
        key = (
            f"smtp_error_{code}"
            if code in supported
            else "smtp_error_generic"
        )
        window.show_status(
            window._t(key)
        )

    mail_scheduler.statusChanged.connect(
        show_mail_status
    )

    mail_scheduler.start()

    app.aboutToQuit.connect(
        mail_scheduler.stop
    )

    def incoming():
        socket = (
            server.nextPendingConnection()
        )

        if socket is None:
            return

        socket.waitForReadyRead(100)

        data = bytes(
            socket.readAll()
        )

        window._raise_window()

        if data == b"quick":
            window.focus_quick_input()

        socket.disconnectFromServer()

    server.newConnection.connect(
        incoming
    )

    window._single_server = server

    screen = app.primaryScreen()

    if screen is not None:
        area = screen.availableGeometry()

        width = min(
            1540,
            max(
                1280,
                area.width() - 90,
            ),
        )

        height = min(
            980,
            max(
                840,
                area.height() - 70,
            ),
        )

        width = min(
            width,
            area.width() - 20,
        )

        height = min(
            height,
            area.height() - 20,
        )

        window.resize(
            QSize(width, height)
        )

        window.move(
            area.x()
            + (
                area.width() - width
            ) // 2,
            area.y()
            + (
                area.height() - height
            ) // 2,
        )

    window.show()

    if "--quick" in sys.argv:
        QTimer.singleShot(
            250,
            window.focus_quick_input,
        )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
