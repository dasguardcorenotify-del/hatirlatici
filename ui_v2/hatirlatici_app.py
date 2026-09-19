#!/usr/bin/env python3
"""Production reminder pages and data-backed dashboard behavior.

``premium_preview`` supplies reusable visual primitives and the common
shell.  This module owns semantic page routing plus CRUD/history/settings
pages.  ``hatirlatici_ultimate`` adds quick entry, advanced actions,
responsive composition, tray behavior, and the only production entry point.
The separation is intentional; no layer installs import-time patches.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import runtime_config
from typing import Dict, List, Optional

from PyQt6.QtCore import QDate, Qt, QTime, QTimer
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

import premium_preview as base
import core_v2 as core


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)
ICON_PATH = ROOT / "assets" / "hatirlatici.svg"

DESKTOP_ENTRY = (
    runtime_config.legacy_dir()
    / "hatirlatici-kur.desktop"
)



def channel_label(
    value: str,
    language: str | None = None,
) -> str:
    return base.channel_label(
        value,
        language or base.runtime_language(),
    )


def channel_icon(value: str) -> str:
    return {
        "email": "mail",
        "pc": "monitor",
        "both": "both",
    }.get(value, "bell")


def service_active(name: str) -> bool:
    settings = runtime_config.load_settings()

    if name == "pc":
        return True

    if name == "mail":
        import credential_vault

        return bool(
            settings.get(
                "email_enabled",
                False,
            )
            and settings.get(
                "email_ready",
                False,
            )
            and settings.get(
                "mail_transport_v2_ready",
                False,
            )
            and credential_vault
            .has_smtp_credential()
        )

    return False


class UnifiedReminderCard(QFrame):
    def __init__(
        self,
        group: Dict[str, object],
        *,
        interactive: bool = False,
        on_edit=None,
        on_toggle=None,
        on_delete=None,
        language: str | None = None,
    ) -> None:
        super().__init__()
        self.language = (
            language
            or base.runtime_language()
        )

        self.setObjectName("ReminderCard")
        self.setMinimumHeight(
            126 if interactive else 112
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            16,
            14,
            14,
            14,
        )
        layout.setSpacing(14)

        channel = str(
            group.get("channel")
            or "email"
        )

        icon = QLabel()
        icon.setObjectName("ReminderIcon")
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

        if isinstance(run_at, dt.datetime):
            when = base.format_datetime(
                run_at,
                self.language,
            )
        else:
            when = base.ui_text(
                "no_schedule",
                self.language,
            )

        time_label = QLabel(when)
        time_label.setObjectName(
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

        meta = QHBoxLayout()
        meta.setSpacing(7)

        tag = QLabel(
            channel_label(
                channel,
                self.language,
            )
        )
        tag.setObjectName("ChannelTag")

        repeat = QLabel(
            base.localized_repeat(
                str(
                    group.get("repeat")
                    or "once"
                ),
                self.language,
            )
        )
        repeat.setObjectName("SecondaryTag")

        state = QLabel(
            base.ui_text(
                "state_active",
                self.language,
            )
            if bool(group.get("enabled"))
            else base.ui_text(
                "state_paused",
                self.language,
            )
        )
        state.setObjectName(
            "StateTagActive"
            if bool(group.get("enabled"))
            else "StateTagPaused"
        )

        meta.addWidget(tag)
        meta.addWidget(repeat)
        meta.addWidget(state)
        meta.addStretch(1)

        middle.addWidget(time_label)
        middle.addWidget(subject)
        middle.addLayout(meta)

        layout.addWidget(icon)
        layout.addLayout(middle, 1)

        if interactive:
            actions = QVBoxLayout()
            actions.setSpacing(5)

            edit = QPushButton(
                base.ui_text(
                    "edit",
                    self.language,
                )
            )
            edit.setObjectName(
                "SecondaryButton"
            )

            toggle = QPushButton(
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
            toggle.setObjectName(
                "SecondaryButton"
            )

            delete = QPushButton(
                base.ui_text(
                    "delete",
                    self.language,
                )
            )
            delete.setObjectName(
                "DangerButton"
            )

            edit.clicked.connect(
                lambda:
                on_edit(group)
                if on_edit
                else None
            )

            toggle.clicked.connect(
                lambda:
                on_toggle(group)
                if on_toggle
                else None
            )

            delete.clicked.connect(
                lambda:
                on_delete(group)
                if on_delete
                else None
            )

            actions.addWidget(edit)
            actions.addWidget(toggle)
            actions.addWidget(delete)

            layout.addLayout(actions)


class EditDialog(QDialog):
    def __init__(
        self,
        parent,
        group: Dict[str, object],
    ) -> None:
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

        self.setWindowTitle(
            self._t("edit_reminder")
        )
        self.setModal(True)
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            24,
            24,
            20,
        )
        layout.setSpacing(10)

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

        row = QHBoxLayout()

        date_col = QVBoxLayout()
        date_col.addWidget(
            QLabel(self._t("date"))
        )

        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setLocale(
            base.qt_locale(self.language)
        )
        self.date.setDisplayFormat(
            "dd MMMM yyyy"
        )
        self.date.setObjectName(
            "DateInput"
        )
        self.date.setMinimumHeight(46)

        time_col = QVBoxLayout()
        time_col.addWidget(
            QLabel(self._t("time"))
        )

        self.time = QTimeEdit()
        self.time.setDisplayFormat("HH:mm")
        self.time.setObjectName(
            "TimeInput"
        )
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

        row.addLayout(date_col, 1)
        row.addLayout(time_col, 1)

        layout.addLayout(row)

        layout.addWidget(
            QLabel(self._t("repeat"))
        )

        self.repeat = QComboBox()
        self.repeat.setObjectName(
            "ComboInput"
        )
        self.repeat.setMinimumHeight(46)
        for repeat_value in base.REPEAT_KEY_BY_VALUE:
            self.repeat.addItem(
                base.localized_repeat(
                    repeat_value,
                    self.language,
                ),
                repeat_value,
            )

        current_repeat = str(
            group.get("repeat")
            or "once"
        )

        repeat_index = self.repeat.findData(
            current_repeat
        )
        self.repeat.setCurrentIndex(
            max(0, repeat_index)
        )

        layout.addWidget(self.repeat)

        layout.addWidget(
            QLabel(self._t("reminder_method"))
        )

        self.channel = QComboBox()
        self.channel.setObjectName(
            "ComboInput"
        )
        self.channel.setMinimumHeight(46)

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

        channel_index = self.channel.findData(
            str(
                group.get("channel")
                or "email"
            )
        )
        self.channel.setCurrentIndex(
            max(0, channel_index)
        )

        layout.addWidget(self.channel)

        layout.addWidget(
            QLabel(self._t("note"))
        )

        self.body = QTextEdit()
        self.body.setObjectName(
            "NoteInput"
        )
        self.body.setText(
            str(
                group.get("body")
                or ""
            )
        )
        self.body.setMinimumHeight(90)

        layout.addWidget(self.body)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(self._t("cancel"))
        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText(self._t("save"))

        buttons.accepted.connect(
            self.accept
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

    def values(self):
        qdate = self.date.date()
        qtime = self.time.time()

        run_at = dt.datetime(
            qdate.year(),
            qdate.month(),
            qdate.day(),
            qtime.hour(),
            qtime.minute(),
        )

        channel = str(
            self.channel.currentData()
            or "email"
        )

        repeat = str(
            self.repeat.currentData()
            or "once"
        )

        return {
            "subject": (
                self.subject.text().strip()
            ),
            "body": (
                self.body
                .toPlainText()
                .strip()
            ),
            "run_at": run_at,
            "channel": channel,
            "repeat": repeat,
        }


class FinalWindow(base.PremiumWindow):
    """Data-backed pages with semantic routing and no translated state."""

    def __init__(self) -> None:
        self.current_page = "today"
        self.final_settings = (
            core.load_settings()
        )
        profile_settings = (
            runtime_config.load_settings()
        )
        profile_channel = str(
            profile_settings.get(
                "default_channel",
                "",
            )
        )
        if profile_channel in base.CHANNEL_KEY_BY_VALUE:
            self.final_settings[
                "default_channel"
            ] = profile_channel

        super().__init__()

        self.setWindowTitle(
            self._t("app_name")
        )

        self.setWindowIcon(
            QIcon(str(ICON_PATH))
        )

        self.apply_final_styles()

    def apply_final_styles(self) -> None:
        self.setStyleSheet(
            self.styleSheet()
            + """
            QLabel#PageTitle {
                color: #F2F7FA;
                font-size: 27px;
                font-weight: 800;
            }

            QLabel#PageSub {
                color: #8C9BA8;
                font-size: 13px;
            }

            QFrame#PagePanel {
                background: #0D161F;
                border: 1px solid #2A3C49;
                border-radius: 14px;
            }

            QScrollArea#PageScroll {
                background: transparent;
                border: none;
            }

            QScrollArea#PageScroll > QWidget > QWidget {
                background: transparent;
            }

            QLabel#SecondaryTag {
                color: #91A2AE;
                background: transparent;
                border: 1px solid #344653;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
            }

            QLabel#StateTagActive {
                color: #67DFA2;
                background: transparent;
                border: 1px solid #287650;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
            }

            QLabel#StateTagPaused {
                color: #E4B96B;
                background: transparent;
                border: 1px solid #735B31;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
            }

            QPushButton#DangerButton {
                background: #171016;
                border: 1px solid #58333A;
                border-radius: 7px;
                color: #DA828B;
                padding: 7px 12px;
                font-size: 12px;
            }

            QPushButton#DangerButton:hover {
                background: #35191F;
                border-color: #92505A;
                color: #FFE5E8;
            }

            QFrame#SettingCard {
                background: #0B151D;
                border: 1px solid #293D49;
                border-radius: 12px;
            }

            QLabel#SettingTitle {
                color: #EAF2F5;
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#SettingDetail {
                color: #84939F;
                font-size: 12px;
            }

            QLabel#HistoryTime {
                color: #27D3D1;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#HistorySubject {
                color: #E8F1F4;
                font-size: 14px;
                font-weight: 700;
            }
            """
        )

    def build_form_card(self) -> QFrame:
        card = super().build_form_card()

        default = str(
            self.final_settings.get(
                "default_channel",
                "email",
            )
        )

        button_id = {
            "email": 0,
            "pc": 1,
            "both": 2,
        }.get(default, 0)

        button = self.delivery_group.button(
            button_id
        )

        if button is not None:
            button.setChecked(True)

        return card

    def active_today(self):
        today = dt.datetime.now().date()

        return [
            group
            for group in core.load_groups(
                active_only=True
            )
            if isinstance(
                group.get("next_run"),
                dt.datetime,
            )
            and group["next_run"].date()
            == today
        ]

    def active_upcoming(self):
        return core.load_groups(
            active_only=True
        )

    def _decorate_new_main(
        self,
        widget: QWidget,
    ) -> None:
        for frame in widget.findChildren(
            QFrame
        ):
            if frame.objectName() not in {
                "Card",
                "InfoStrip",
                "PagePanel",
            }:
                continue

            shadow = base.QGraphicsDropShadowEffect(
                frame
            )

            shadow.setBlurRadius(28)
            shadow.setOffset(0, 7)
            shadow.setColor(
                QColor(0, 0, 0, 110)
            )

            frame.setGraphicsEffect(
                shadow
            )

    def switch_page(
        self,
        page_id: str,
    ) -> None:
        builders = {
            "today": self.build_main,
            "reminders": (
                self.build_reminders_page
            ),
            "history": (
                self.build_history_page
            ),
            "settings": (
                self.build_settings_page
            ),
        }

        if page_id not in builders:
            return

        self.current_page = page_id

        for button in self.nav_buttons:
            button.set_active(
                button.page_id == page_id
            )

        old = self.main_widget
        new = builders[page_id]()

        self.body_layout.replaceWidget(
            old,
            new,
        )

        old.hide()
        old.deleteLater()

        self.main_widget = new

        self._decorate_new_main(new)

    def activate_nav(
        self,
        selected,
    ) -> None:
        self.switch_page(
            selected.page_id
        )

    def delivery_changed(
        self,
        button,
    ) -> None:
        checked = (
            self.delivery_group.checkedId()
        )

        channel = {
            0: "email",
            1: "pc",
            2: "both",
        }.get(checked, "email")
        text = self._t(
            "channel_selected",
            channel=channel_label(
                channel,
                self.language,
            ),
        )
        self.channel_info.setText(
            "ⓘ   " + text
        )

        self.show_status(text)

    def _channel_from_group(self) -> str:
        return {
            0: "email",
            1: "pc",
            2: "both",
        }.get(
            self.delivery_group.checkedId(),
            "email",
        )

    def preview_save(self) -> None:
        subject = (
            self.subject_edit
            .text()
            .strip()
        )

        if not subject:
            self.show_status(
                self._t("title_required")
            )
            self.subject_edit.setFocus()
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

        try:
            pair_id = core.save_group(
                pair_id=None,
                channel=(
                    self._channel_from_group()
                ),
                subject=subject,
                body=(
                    self.note_edit
                    .toPlainText()
                    .strip()
                ),
                run_at=run_at,
                repeat=repeat,
            )

        except Exception as exc:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t("operation_failed_detail"),
                )
            )
            return

        channel = (
            self._channel_from_group()
        )

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
            + f" • {pair_id[:8]}"
        )

    def focus_new_reminder(self) -> None:
        if self.current_page != "today":
            self.switch_page("today")

        QTimer.singleShot(
            0,
            lambda:
            self.subject_edit.setFocus()
        )

    def build_today_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            20,
            22,
            20,
            18,
        )
        layout.setSpacing(13)

        header = QHBoxLayout()

        icon = QLabel()
        icon.setPixmap(
            base.make_line_icon(
                "calendar",
                "#EAF4F8",
                20,
            ).pixmap(20, 20)
        )

        title = QLabel(self._t("nav_today"))
        title.setObjectName(
            "SectionTitle"
        )

        all_button = QPushButton(
            self._t("view_all") + "   ›"
        )
        all_button.setObjectName(
            "SecondaryButton"
        )
        all_button.setFixedHeight(38)
        all_button.clicked.connect(
            lambda:
            self.switch_page(
                "reminders"
            )
        )

        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(all_button)

        layout.addLayout(header)

        groups = self.active_today()

        if not groups:
            quiet = QFrame()
            quiet.setObjectName(
                "QuietState"
            )

            ql = QVBoxLayout(quiet)
            ql.setContentsMargins(
                18,
                24,
                18,
                24,
            )

            check = QLabel("✓")
            check.setObjectName(
                "QuietIcon"
            )
            check.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            qt = QLabel(
                self._t("today_no_active")
            )
            qt.setObjectName(
                "QuietTitle"
            )
            qt.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            qd = QLabel(
                self._t("reminders_appear_here")
            )
            qd.setObjectName(
                "QuietDetail"
            )
            qd.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            ql.addWidget(check)
            ql.addWidget(qt)
            ql.addWidget(qd)

            layout.addWidget(quiet)

        else:
            for group in groups[:3]:
                layout.addWidget(
                    UnifiedReminderCard(
                        group,
                        language=self.language,
                    )
                )

        all_groups = core.load_groups()

        mail_sends = 0
        pc_sends = 0

        last_values: List[dt.datetime] = []

        for group in all_groups:
            mail = group.get("mail_row")
            pc = group.get("pc_row")

            if isinstance(mail, dict):
                try:
                    mail_sends += int(
                        mail.get(
                            "send_count",
                            "0",
                        )
                        or 0
                    )
                except ValueError:
                    pass

                sent = core.parse_dt(
                    mail.get(
                        "last_sent",
                        "",
                    )
                )
                if sent:
                    last_values.append(sent)

            if isinstance(pc, dict):
                try:
                    pc_sends += int(
                        pc.get(
                            "send_count",
                            "0",
                        )
                        or 0
                    )
                except ValueError:
                    pass

                sent = core.parse_dt(
                    pc.get(
                        "last_sent",
                        "",
                    )
                )
                if sent:
                    last_values.append(sent)

        summary = QFrame()
        summary.setObjectName(
            "SystemSummary"
        )

        sl = QVBoxLayout(summary)
        sl.setContentsMargins(
            15,
            13,
            15,
            13,
        )
        sl.setSpacing(9)

        sh = QHBoxLayout()

        st = QLabel(self._t("system_summary"))
        st.setObjectName(
            "SystemSummaryTitle"
        )

        live = QLabel(self._t("system_status"))
        live.setObjectName(
            "SystemLivePill"
        )

        sh.addWidget(st)
        sh.addStretch(1)
        sh.addWidget(live)

        sl.addLayout(sh)

        stats = QHBoxLayout()
        stats.setSpacing(7)

        last_text = (
            base.format_datetime(
                max(last_values),
                self.language,
            )
            if last_values
            else self._t("none_yet")
        )

        values = (
            (
                str(
                    len(
                        core.load_groups(
                            active_only=True
                        )
                    )
                ),
                self._t("stat_active"),
            ),
            (
                str(mail_sends),
                self._t("delivery_email"),
            ),
            (
                str(pc_sends),
                self._t("delivery_pc"),
            ),
            (
                last_text,
                self._t("stat_last_delivery"),
            ),
        )

        for value_text, label_text in values:
            cell = QFrame()
            cell.setObjectName("StatCell")

            cl = QVBoxLayout(cell)
            cl.setContentsMargins(
                9,
                8,
                9,
                8,
            )
            cl.setSpacing(2)

            value = QLabel(value_text)
            value.setObjectName(
                "StatValue"
            )

            label = QLabel(label_text)
            label.setObjectName(
                "StatLabel"
            )
            label.setWordWrap(True)
            label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            cl.addWidget(value)
            cl.addWidget(label)

            stats.addWidget(cell, 1)

        sl.addLayout(stats)

        layout.addWidget(summary)
        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName(
            "RightFooter"
        )

        fl = QHBoxLayout(footer)
        fl.setContentsMargins(
            13,
            10,
            13,
            10,
        )

        fi = QLabel()
        fi.setPixmap(
            base.make_line_icon(
                "bell",
                "#27D3D1",
                20,
            ).pixmap(20, 20)
        )

        ft = QLabel(
            self._t("channels_independent")
        )
        ft.setObjectName(
            "FooterText"
        )
        ft.setWordWrap(True)

        fl.addWidget(fi)
        fl.addWidget(ft, 1)

        layout.addWidget(footer)

        return card

    def _page_shell(
        self,
        title: str,
        subtitle: str,
    ):
        page = QFrame()
        page.setObjectName("Main")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            34,
            30,
            34,
            26,
        )
        layout.setSpacing(16)

        heading = QLabel(title)
        heading.setObjectName(
            "PageTitle"
        )

        sub = QLabel(subtitle)
        sub.setObjectName(
            "PageSub"
        )

        layout.addWidget(heading)
        layout.addWidget(sub)

        return page, layout

    def build_reminders_page(self):
        page, layout = self._page_shell(
            self._t("nav_reminders"),
            self._t("reminders_subtitle"),
        )

        filter_row = QHBoxLayout()

        filter_label = QLabel(
            self._t("filter_show")
        )

        combo = QComboBox()
        combo.setObjectName(
            "ComboInput"
        )
        combo.setFixedWidth(180)
        combo.setMinimumHeight(40)
        combo.addItem(
            self._t("filter_all"),
            "all",
        )
        for channel_value in (
            "email",
            "pc",
            "both",
        ):
            combo.addItem(
                channel_label(
                    channel_value,
                    self.language,
                ),
                channel_value,
            )

        refresh = QPushButton(
            self._t("refresh")
        )
        refresh.setObjectName(
            "SecondaryButton"
        )

        filter_row.addWidget(
            filter_label
        )
        filter_row.addWidget(combo)
        filter_row.addStretch(1)
        filter_row.addWidget(refresh)

        layout.addLayout(filter_row)

        scroll = QScrollArea()
        scroll.setObjectName(
            "PageScroll"
        )
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        cards = QVBoxLayout(container)
        cards.setContentsMargins(
            0,
            4,
            0,
            4,
        )
        cards.setSpacing(10)

        scroll.setWidget(container)

        layout.addWidget(
            scroll,
            1,
        )

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
                widget = item.widget()

                if widget:
                    widget.deleteLater()

        def render():
            clear_cards()

            groups = core.load_groups()

            wanted = combo.currentData()

            if wanted != "all":
                groups = [
                    group
                    for group in groups
                    if group.get("channel")
                    == wanted
                ]

            if not groups:
                empty = QLabel(
                    self._t("no_filter_match")
                )
                empty.setObjectName(
                    "PageSub"
                )
                empty.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                cards.addWidget(empty)

            for group in groups:
                cards.addWidget(
                    UnifiedReminderCard(
                        group,
                        interactive=True,
                        on_edit=self._edit_group,
                        on_toggle=self._toggle_group,
                        on_delete=self._delete_group,
                        language=self.language,
                    )
                )

            cards.addStretch(1)

        combo.currentTextChanged.connect(
            lambda _:
            render()
        )

        refresh.clicked.connect(
            render
        )

        render()

        return page

    def _edit_group(
        self,
        group: Dict[str, object],
    ) -> None:
        dialog = EditDialog(
            self,
            group,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()

        try:
            core.save_group(
                pair_id=str(
                    group["pair_id"]
                ),
                channel=values["channel"],
                subject=values["subject"],
                body=values["body"],
                run_at=values["run_at"],
                repeat=values["repeat"],
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._t("edit_reminder"),
                self._t(
                    "update_failed",
                    error=self._t("operation_failed_detail"),
                ),
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ " + self._t("reminder_updated")
        )

    def _toggle_group(
        self,
        group: Dict[str, object],
    ) -> None:
        new_state = not bool(
            group.get("enabled")
        )

        try:
            core.set_group_enabled(
                str(
                    group["pair_id"]
                ),
                new_state,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._t("nav_reminders"),
                self._t(
                    "update_failed",
                    error=self._t("operation_failed_detail"),
                ),
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ "
            + self._t(
                "state_active"
                if new_state
                else "state_paused"
            )
        )

    def _delete_group(
        self,
        group: Dict[str, object],
    ) -> None:
        answer = QMessageBox.question(
            self,
            self._t("delete_reminder"),
            self._t(
                "delete_confirm",
                subject=str(
                    group.get("subject")
                    or self._t("untitled_reminder")
                ),
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            core.delete_group(
                str(
                    group["pair_id"]
                )
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self._t("delete_reminder"),
                self._t(
                    "delete_failed",
                    error=self._t("operation_failed_detail"),
                ),
            )
            return

        self.switch_page(
            "reminders"
        )

        self.show_status(
            "✓ " + self._t("reminder_deleted")
        )

    def build_history_page(self):
        page, layout = self._page_shell(
            self._t("nav_history"),
            self._t("history_subtitle"),
        )

        summary = QFrame()
        summary.setObjectName(
            "PagePanel"
        )

        sl = QVBoxLayout(summary)
        sl.setContentsMargins(
            18,
            15,
            18,
            15,
        )

        total_old = 0
        latest_old: Optional[dt.datetime] = None

        for group in core.load_groups():
            for key in (
                "mail_row",
                "pc_row",
            ):
                row = group.get(key)

                if not isinstance(row, dict):
                    continue

                try:
                    total_old += int(
                        row.get(
                            "send_count",
                            "0",
                        )
                        or 0
                    )
                except ValueError:
                    pass

                sent = core.parse_dt(
                    row.get(
                        "last_sent",
                        "",
                    )
                )

                if sent and (
                    latest_old is None
                    or sent > latest_old
                ):
                    latest_old = sent

        title = QLabel(
            self._t("history_counts_title")
        )
        title.setObjectName(
            "SettingTitle"
        )

        count_text = (
            self._t(
                "history_counts_last",
                count=total_old,
                last=base.format_datetime(
                    latest_old,
                    self.language,
                ),
            )
            if latest_old
            else self._t(
                "history_counts",
                count=total_old,
            )
        )
        detail = QLabel(
            count_text
            + "\n"
            + self._t("history_truth_note")
        )
        detail.setObjectName(
            "SettingDetail"
        )
        detail.setWordWrap(True)

        sl.addWidget(title)
        sl.addWidget(detail)

        layout.addWidget(summary)

        scroll = QScrollArea()
        scroll.setObjectName(
            "PageScroll"
        )
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        cards = QVBoxLayout(container)
        cards.setContentsMargins(
            0,
            4,
            0,
            4,
        )
        cards.setSpacing(9)

        history = core.load_history()

        if not history:
            empty = QLabel(
                self._t("history_empty")
            )
            empty.setObjectName(
                "PageSub"
            )
            empty.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            cards.addWidget(empty)

        for event in history:
            card = QFrame()
            card.setObjectName(
                "ReminderCard"
            )

            cl = QHBoxLayout(card)
            cl.setContentsMargins(
                16,
                12,
                16,
                12,
            )
            cl.setSpacing(13)

            icon = QLabel()
            icon.setFixedSize(44, 44)
            icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            icon.setPixmap(
                base.make_line_icon(
                    channel_icon(
                        event.get(
                            "channel",
                            "email",
                        )
                    ),
                    "#27D3D1",
                    23,
                ).pixmap(23, 23)
            )

            texts = QVBoxLayout()

            sent_at = core.parse_dt(
                event.get(
                    "sent_at",
                    "",
                )
            )
            when = QLabel(
                base.format_datetime(
                    sent_at,
                    self.language,
                )
                if sent_at
                else "—"
            )
            when.setObjectName(
                "HistoryTime"
            )

            subject = QLabel(
                event.get(
                    "subject",
                    self._t("reminder_fallback"),
                )
            )
            subject.setObjectName(
                "HistorySubject"
            )
            subject.setWordWrap(True)

            channel = QLabel(
                channel_label(
                    event.get(
                        "channel",
                        "email",
                    ),
                    self.language,
                )
            )
            channel.setObjectName(
                "ChannelTag"
            )

            texts.addWidget(when)
            texts.addWidget(subject)
            texts.addWidget(
                channel,
                alignment=(
                    Qt.AlignmentFlag.AlignLeft
                ),
            )

            cl.addWidget(icon)
            cl.addLayout(texts, 1)

            cards.addWidget(card)

        cards.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.preview_status = QLabel("")
        self.preview_status.setObjectName(
            "PreviewStatus"
        )
        layout.addWidget(
            self.preview_status
        )

        return page

    def _setting_card(
        self,
        title: str,
        detail: str,
    ):
        card = QFrame()
        card.setObjectName(
            "SettingCard"
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            18,
            15,
            18,
            15,
        )
        layout.setSpacing(12)

        texts = QVBoxLayout()

        t = QLabel(title)
        t.setObjectName(
            "SettingTitle"
        )
        t.setWordWrap(True)

        d = QLabel(detail)
        d.setObjectName(
            "SettingDetail"
        )
        d.setWordWrap(True)

        texts.addWidget(t)
        texts.addWidget(d)

        layout.addLayout(texts, 1)

        return card, layout

    def build_settings_page(self):
        page, layout = self._page_shell(
            self._t("nav_settings"),
            self._t("settings_subtitle"),
        )

        mail_ok = service_active(
            "mail"
        )

        pc_ok = service_active(
            "pc"
        )

        status_card, status_layout = (
            self._setting_card(
                self._t("delivery_engines"),
                self._t(
                    "delivery_engine_status",
                    email=self._t(
                        "running"
                        if mail_ok
                        else "stopped"
                    ),
                    computer=self._t(
                        "running"
                        if pc_ok
                        else "stopped"
                    ),
                ),
            )
        )

        badge = QLabel(
            self._t("healthy")
            if mail_ok and pc_ok
            else self._t("check_status")
        )
        badge.setObjectName(
            "SystemLivePill"
        )

        status_layout.addWidget(badge)
        layout.addWidget(status_card)

        channel_card, channel_layout = (
            self._setting_card(
                self._t("default_method_title"),
                self._t("default_method_detail"),
            )
        )

        channel_combo = QComboBox()
        channel_combo.setObjectName(
            "ComboInput"
        )
        channel_combo.setMinimumHeight(40)

        for channel_value in (
            "email",
            "pc",
            "both",
        ):
            channel_combo.addItem(
                channel_label(
                    channel_value,
                    self.language,
                ),
                channel_value,
            )

        default_channel = str(
            self.final_settings.get(
                "default_channel",
                self.default_channel,
            )
        )
        channel_combo.setCurrentIndex(
            max(
                0,
                channel_combo.findData(
                    default_channel
                ),
            )
        )

        save_channel = QPushButton(
            self._t("save")
        )
        save_channel.setObjectName(
            "SecondaryButton"
        )

        channel_layout.addWidget(
            channel_combo
        )
        channel_layout.addWidget(
            save_channel
        )

        def save_default():
            value = str(
                channel_combo.currentData()
                or "email"
            )

            core.save_settings(
                {
                    "default_channel": value
                }
            )

            profile_settings = (
                runtime_config.load_settings()
            )
            profile_settings[
                "default_channel"
            ] = value
            runtime_config.save_settings(
                profile_settings
            )
            self.default_channel = value

            self.final_settings = (
                core.load_settings()
            )

            self.show_status(
                "✓ "
                + self._t(
                    "default_method_saved"
                )
            )

        save_channel.clicked.connect(
            save_default
        )

        layout.addWidget(channel_card)

        notify_card, notify_layout = (
            self._setting_card(
                self._t("notification_test_title"),
                self._t("notification_test_detail"),
            )
        )

        test_button = QPushButton(
            self._t("notification_test_send")
        )
        test_button.setObjectName(
            "SecondaryButton"
        )

        notify_layout.addWidget(
            test_button
        )

        def test_notification():
            import portal_notifications
            from PyQt6.QtWidgets import QMessageBox

            try:
                portal_notifications.add_notification(
                    "settings-notification-test",
                    self._t("notification_test_heading"),
                    self._t("notification_test_body"),
                    action_buttons=False,
                )

            except portal_notifications.PortalNotificationError as exc:
                QMessageBox.warning(
                    None,
                    self._t("notification_test_failed"),
                    self._t(
                        "notification_test_failed_detail"
                    ),
                )
                return

            QMessageBox.information(
                None,
                self._t("notification_test_ok"),
                self._t("notification_test_sent"),
            )

        test_button.clicked.connect(
            test_notification
        )

        layout.addWidget(notify_card)

        autostart_card, autostart_layout = (
            self._setting_card(
                self._t("autostart_title"),
                self._t("autostart_detail"),
            )
        )

        autostart = QPushButton()
        autostart.setObjectName(
            "SecondaryButton"
        )

        def sync_autostart_text():
            settings = runtime_config.load_settings()

            background_ok = bool(
                settings.get(
                    "background_allowed",
                    False,
                )
            )

            autostart_ok = bool(
                settings.get(
                    "background_autostart",
                    False,
                )
            )

            if background_ok and autostart_ok:
                autostart.setText(
                    self._t(
                        "background_on_autostart_on"
                    )
                )
            elif background_ok:
                autostart.setText(
                    self._t("background_on")
                )
            else:
                autostart.setText(
                    self._t("background_request")
                )

        sync_autostart_text()

        def toggle_autostart():
            import background_portal
            from PyQt6.QtWidgets import QMessageBox

            if not background_portal.is_flatpak():
                QMessageBox.information(
                    self,
                    self._t("background_permission_title"),
                    self._t("background_development_note"),
                )
                return

            settings = runtime_config.load_settings()

            current_autostart = bool(
                settings.get(
                    "background_autostart",
                    False,
                )
            )

            try:
                result = background_portal.request_background(
                    reason=(
                        self._t("background_reason")
                    ),
                    autostart=(
                        not current_autostart
                    ),
                )

            except background_portal.BackgroundPortalError as exc:
                QMessageBox.warning(
                    self,
                    self._t("background_permission_title"),
                    self._t("background_request_failed"),
                )
                return

            settings["background_allowed"] = bool(
                result.background
            )

            settings["background_autostart"] = bool(
                result.autostart
            )

            runtime_config.save_settings(
                settings
            )

            sync_autostart_text()

            if not result.success or not result.background:
                QMessageBox.warning(
                    self,
                    self._t("background_permission_title"),
                    self._t("background_denied"),
                )

        autostart.clicked.connect(
            toggle_autostart
        )

        autostart_layout.addWidget(
            autostart
        )

        layout.addWidget(autostart_card)

        layout.addStretch(1)

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

        return page


def main() -> int:
    """Compatibility entry that always delegates to production.

    Keeping this callable supports old development commands without
    maintaining a second window lifecycle, server namespace, or scheduler
    path.  Packaging launches ``hatirlatici_ultimate.main`` directly.
    """
    from hatirlatici_ultimate import main as production_main

    return production_main()


if __name__ == "__main__":
    raise SystemExit(main())
