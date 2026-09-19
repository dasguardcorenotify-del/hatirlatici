#!/usr/bin/env python3

from __future__ import annotations

import csv
import datetime as dt
import fcntl
import html
import os
import shutil
import tempfile
from pathlib import Path

import runtime_config
import l10n
from typing import Dict, List

from PyQt6.QtCore import QDate, QLocale, QPoint, QRectF, QSize, Qt, QTime, QTimer
from PyQt6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QGraphicsDropShadowEffect,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


CSV_PATH = runtime_config.mail_csv_path()
LOCK_PATH = runtime_config.mail_lock_path()
BACKUP_PATH = runtime_config.data_backups_dir()

TIME_FMT = "%Y-%m-%d %H:%M"

REQUIRED_FIELDS = [
    "id",
    "enabled",
    "next_run",
    "repeat",
    "snooze_until",
    "last_sent",
    "send_count",
    "subject",
    "body",
]

REPEAT_KEY_BY_VALUE = {
    "once": "repeat_once",
    "daily": "repeat_daily",
    "weekly": "repeat_weekly",
    "monthly": "repeat_monthly",
    "every 15m": "repeat_every_15m",
    "every 30m": "repeat_every_30m",
    "every 1h": "repeat_every_1h",
    "every 2h": "repeat_every_2h",
}

CHANNEL_KEY_BY_VALUE = {
    "email": "delivery_email",
    "pc": "delivery_pc",
    "both": "delivery_both",
}

CATEGORY_KEY_BY_VALUE = {
    "Genel": "category_general",
    "Kişisel": "category_personal",
    "İş": "category_work",
    "Ödeme": "category_payment",
    "Sağlık": "category_health",
    "Alışveriş": "category_shopping",
    "Diğer": "category_other",
}

PAGE_LABEL_KEY = {
    "today": "nav_today",
    "reminders": "nav_reminders",
    "history": "nav_history",
    "settings": "nav_settings",
}

QT_LOCALE_BY_LANGUAGE = {
    "tr": "tr_TR",
    "en": "en_US",
    "de": "de_DE",
    "es": "es_ES",
    "ru": "ru_RU",
}


def runtime_language() -> str:
    """Return the persisted application language, never a display label."""
    return l10n.normalize_language(
        runtime_config.load_settings().get(
            "language",
            "en",
        )
    )


def ui_text(
    key: str,
    language: str | None = None,
    **values: object,
) -> str:
    return l10n.text(
        key,
        language or runtime_language(),
        **values,
    )


def localized_repeat(
    value: str,
    language: str,
) -> str:
    key = REPEAT_KEY_BY_VALUE.get(value)
    return ui_text(key, language) if key else value


def channel_label(
    value: str,
    language: str,
) -> str:
    key = CHANNEL_KEY_BY_VALUE.get(value)
    return ui_text(key, language) if key else value


def localized_category(
    value: str,
    language: str,
) -> str:
    key = CATEGORY_KEY_BY_VALUE.get(value)
    return ui_text(key, language) if key else value


def qt_locale(language: str) -> QLocale:
    return QLocale(
        QT_LOCALE_BY_LANGUAGE.get(
            l10n.normalize_language(language),
            "en_US",
        )
    )


def format_datetime(
    value: dt.datetime,
    language: str,
) -> str:
    locale = qt_locale(language)
    date_text = locale.toString(
        QDate(
            value.year,
            value.month,
            value.day,
        ),
        QLocale.FormatType.ShortFormat,
    )
    return f"{date_text} • {value:%H:%M}"


def localized_today_count(
    count: int,
    language: str,
) -> str:
    """Format today's count with the locale's grammatical number."""
    normalized = l10n.normalize_language(language)
    value = max(0, int(count))
    if value == 1 or (
        normalized == "ru"
        and value % 10 == 1
        and value % 100 != 11
    ):
        form = "one"
    elif (
        normalized == "ru"
        and value % 10 in (2, 3, 4)
        and value % 100 not in (12, 13, 14)
    ):
        form = "few"
    else:
        form = "many"
    return ui_text(
        f"today_count_{form}",
        normalized,
        count=value,
    )


COLORS = {
    "window": "#060A0F",
    "root": "#080D13",
    "sidebar": "#090F16",
    "panel": "#0D151E",
    "panel_2": "#101A25",
    "input": "#0B131C",
    "input_hover": "#101B27",
    "border": "#263442",
    "border_soft": "#1B2834",
    "text": "#F2F7FA",
    "muted": "#95A3B2",
    "muted_2": "#687786",
    "accent": "#27D3D1",
    "accent_2": "#13A9B1",
    "accent_dark": "#0F6972",
    "success": "#60D394",
}


def select_font() -> str:
    families = set(QFontDatabase.families())
    for candidate in (
        "Inter",
        "Noto Sans",
        "IBM Plex Sans",
        "Ubuntu",
        "DejaVu Sans",
    ):
        if candidate in families:
            return candidate
    return QApplication.font().family()


def make_line_icon(
    kind: str,
    color: str = "#27D3D1",
    size: int = 20,
) -> QIcon:
    """Small dependency-free antialiased line icon set."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    pen = QPen(QColor(color))
    pen.setWidthF(max(1.45, size * 0.078))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    s = float(size)

    if kind == "mail":
        r = QRectF(s * .13, s * .24, s * .74, s * .52)
        p.drawRoundedRect(r, s * .07, s * .07)
        p.drawLine(
            int(s * .16), int(s * .30),
            int(s * .50), int(s * .54),
        )
        p.drawLine(
            int(s * .84), int(s * .30),
            int(s * .50), int(s * .54),
        )

    elif kind == "monitor":
        r = QRectF(s * .13, s * .16, s * .74, s * .52)
        p.drawRoundedRect(r, s * .06, s * .06)
        p.drawLine(
            int(s * .50), int(s * .69),
            int(s * .50), int(s * .82),
        )
        p.drawLine(
            int(s * .34), int(s * .83),
            int(s * .66), int(s * .83),
        )

    elif kind == "both":
        r1 = QRectF(s * .08, s * .25, s * .44, s * .34)
        p.drawRoundedRect(r1, s * .04, s * .04)
        p.drawLine(
            int(s * .10), int(s * .28),
            int(s * .30), int(s * .43),
        )
        p.drawLine(
            int(s * .50), int(s * .28),
            int(s * .30), int(s * .43),
        )

        r2 = QRectF(s * .48, s * .44, s * .44, s * .36)
        p.drawRoundedRect(r2, s * .04, s * .04)
        p.drawLine(
            int(s * .70), int(s * .80),
            int(s * .70), int(s * .89),
        )

    elif kind in {"calendar", "calendar_plus"}:
        r = QRectF(s * .17, s * .20, s * .66, s * .64)
        p.drawRoundedRect(r, s * .07, s * .07)

        p.drawLine(
            int(s * .17), int(s * .37),
            int(s * .83), int(s * .37),
        )
        p.drawLine(
            int(s * .32), int(s * .13),
            int(s * .32), int(s * .29),
        )
        p.drawLine(
            int(s * .68), int(s * .13),
            int(s * .68), int(s * .29),
        )

        if kind == "calendar_plus":
            p.drawLine(
                int(s * .50), int(s * .49),
                int(s * .50), int(s * .70),
            )
            p.drawLine(
                int(s * .40), int(s * .595),
                int(s * .60), int(s * .595),
            )

    elif kind == "bell":
        p.drawArc(
            QRectF(s * .25, s * .18, s * .50, s * .55),
            0,
            180 * 16,
        )
        p.drawLine(
            int(s * .25), int(s * .46),
            int(s * .25), int(s * .68),
        )
        p.drawLine(
            int(s * .75), int(s * .46),
            int(s * .75), int(s * .68),
        )
        p.drawLine(
            int(s * .20), int(s * .70),
            int(s * .80), int(s * .70),
        )
        p.drawArc(
            QRectF(s * .43, s * .68, s * .14, s * .14),
            180 * 16,
            180 * 16,
        )

    elif kind == "history":
        p.drawArc(
            QRectF(s * .16, s * .16, s * .68, s * .68),
            35 * 16,
            300 * 16,
        )
        p.drawLine(
            int(s * .18), int(s * .31),
            int(s * .10), int(s * .22),
        )
        p.drawLine(
            int(s * .18), int(s * .31),
            int(s * .29), int(s * .27),
        )
        p.drawLine(
            int(s * .50), int(s * .34),
            int(s * .50), int(s * .53),
        )
        p.drawLine(
            int(s * .50), int(s * .53),
            int(s * .64), int(s * .60),
        )

    elif kind == "settings":
        p.drawEllipse(
            QRectF(s * .34, s * .34, s * .32, s * .32)
        )
        for x1, y1, x2, y2 in (
            (.50, .09, .50, .25),
            (.50, .75, .50, .91),
            (.09, .50, .25, .50),
            (.75, .50, .91, .50),
            (.20, .20, .31, .31),
            (.69, .69, .80, .80),
            (.69, .31, .80, .20),
            (.20, .80, .31, .69),
        ):
            p.drawLine(
                int(s * x1), int(s * y1),
                int(s * x2), int(s * y2),
            )

    elif kind == "local":
        # Local/private storage symbol.
        r = QRectF(s * .22, s * .17, s * .56, s * .67)
        p.drawRoundedRect(r, s * .08, s * .08)
        p.drawEllipse(
            QRectF(s * .43, s * .58, s * .14, s * .14)
        )
        p.drawLine(
            int(s * .34), int(s * .34),
            int(s * .66), int(s * .34),
        )

    else:
        p.drawEllipse(
            QRectF(s * .25, s * .25, s * .50, s * .50)
        )

    p.end()

    return QIcon(pixmap)


def parse_dt(value: str) -> dt.datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, TIME_FMT)
    except ValueError:
        return None


def load_rows() -> List[Dict[str, str]]:
    if not CSV_PATH.exists():
        return []

    try:
        with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _next_id(rows: List[Dict[str, str]]) -> int:
    highest = 0

    for row in rows:
        try:
            highest = max(
                highest,
                int((row.get("id") or "0").strip()),
            )
        except ValueError:
            continue

    return highest + 1


def _backup_live_csv(path: Path) -> None:
    if not path.exists():
        return

    BACKUP_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = dt.datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    target = (
        BACKUP_PATH
        / f"hatirlatmalar_before_write_{stamp}.csv"
    )

    shutil.copy2(path, target)

    backups = sorted(
        BACKUP_PATH.glob(
            "hatirlatmalar_before_write_*.csv"
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Son 20 otomatik veri yedeği tutulur.
    for old in backups[20:]:
        try:
            old.unlink()
        except OSError:
            pass


def append_email_reminder(
    path: Path,
    subject: str,
    body: str,
    run_at: dt.datetime,
    repeat: str,
) -> int:
    subject = subject.strip()
    body = body.strip()

    if not subject:
        raise ValueError(
            "Hatırlatma başlığı boş olamaz."
        )

    now = dt.datetime.now().replace(
        second=0,
        microsecond=0,
    )

    if run_at <= now:
        raise ValueError(
            "Hatırlatma zamanı gelecekte olmalı."
        )

    if repeat not in {
        "once",
        "daily",
        "weekly",
        "monthly",
        "every 15m",
        "every 30m",
        "every 1h",
        "every 2h",
    }:
        raise ValueError(
            "Geçersiz tekrar seçeneği."
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOCK_PATH.touch(
        exist_ok=True,
    )

    with LOCK_PATH.open("a+") as lock:
        # Aynı kilidi teslimat motoru da kullanır.
        fcntl.flock(
            lock.fileno(),
            fcntl.LOCK_EX,
        )

        try:
            if path.exists():
                with path.open(
                    "r",
                    encoding="utf-8",
                    newline="",
                ) as f:
                    reader = csv.DictReader(f)
                    fieldnames = list(
                        reader.fieldnames or []
                    )
                    rows = list(reader)
            else:
                fieldnames = list(REQUIRED_FIELDS)
                rows = []

            missing = [
                field
                for field in REQUIRED_FIELDS
                if field not in fieldnames
            ]

            if missing:
                raise RuntimeError(
                    "CSV sözleşmesi bozuk. "
                    "Eksik alanlar: "
                    + ", ".join(missing)
                )

            reminder_id = _next_id(rows)

            row = {
                field: ""
                for field in fieldnames
            }

            row.update(
                {
                    "id": str(reminder_id),
                    "enabled": "1",
                    "next_run": run_at.strftime(
                        TIME_FMT
                    ),
                    "repeat": repeat,
                    "snooze_until": "",
                    "last_sent": "",
                    "send_count": "0",
                    "subject": subject,
                    "body": body or subject,
                }
            )

            new_rows = rows + [row]

            _backup_live_csv(path)

            temp_name = None

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    newline="",
                    dir=str(path.parent),
                    prefix=".hatirlatmalar.ui.",
                    suffix=".tmp",
                    delete=False,
                ) as temp:
                    temp_name = temp.name

                    writer = csv.DictWriter(
                        temp,
                        fieldnames=fieldnames,
                    )

                    writer.writeheader()
                    writer.writerows(new_rows)

                    temp.flush()
                    os.fsync(temp.fileno())

                os.replace(
                    temp_name,
                    path,
                )

                # Directory metadata durability.
                dir_fd = os.open(
                    str(path.parent),
                    os.O_DIRECTORY,
                )

                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)

            finally:
                if (
                    temp_name
                    and os.path.exists(temp_name)
                ):
                    try:
                        os.unlink(temp_name)
                    except OSError:
                        pass

            return reminder_id

        finally:
            fcntl.flock(
                lock.fileno(),
                fcntl.LOCK_UN,
            )


class TitleBar(QFrame):
    # LEFT_CONTROLS_V2
    def __init__(self, window: "PremiumWindow") -> None:
        super().__init__()

        self.window_ref = window
        self.drag_offset: QPoint | None = None

        self.setObjectName("TitleBar")
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        # -------------------------------------------------
        # USER DESKTOP PREFERENCE:
        # Close / minimize / maximize controls are LEFT.
        # -------------------------------------------------

        left_cluster = QWidget()
        left_cluster.setObjectName("LeftWindowControls")
        left_cluster.setFixedWidth(176)

        left_layout = QHBoxLayout(left_cluster)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        btn_close = QPushButton("×")
        btn_min = QPushButton("—")
        btn_max = QPushButton("□")

        btn_close.setObjectName("WindowControl")
        btn_min.setObjectName("WindowControl")
        btn_max.setObjectName("WindowControl")

        btn_close.setProperty("danger", "true")
        btn_min.setProperty("controlRole", "minimize")
        btn_max.setProperty("controlRole", "maximize")

        btn_close.setToolTip(window._t("window_close"))
        btn_min.setToolTip(window._t("window_minimize"))
        btn_max.setToolTip(window._t("window_maximize_restore"))

        btn_close.setAccessibleName(window._t("window_close"))
        btn_min.setAccessibleName(window._t("window_minimize"))
        btn_max.setAccessibleName(window._t("window_maximize_restore"))

        for button in (
            btn_close,
            btn_min,
            btn_max,
        ):
            button.setFixedSize(34, 30)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_close.clicked.connect(window.close)
        btn_min.clicked.connect(window.showMinimized)
        btn_max.clicked.connect(window.toggle_maximize)

        app_mark = QLabel()
        app_mark.setObjectName("TitleMark")
        app_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_mark.setFixedSize(30, 30)
        app_mark.setPixmap(
            make_line_icon(
                "bell",
                "#27D3D1",
                17,
            ).pixmap(17, 17)
        )

        left_layout.addWidget(btn_close)
        left_layout.addWidget(btn_min)
        left_layout.addWidget(btn_max)
        left_layout.addSpacing(8)
        left_layout.addWidget(app_mark)
        left_layout.addStretch(1)

        title = QLabel(window._t("app_name"))
        title.setObjectName("WindowTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sağ tarafta aynı genişlikte görünmez denge alanı.
        # Böylece başlık gerçekten geometrik merkezde kalır.
        right_balance = QWidget()
        right_balance.setObjectName("RightTitleBalance")
        right_balance.setFixedWidth(176)

        layout.addWidget(left_cluster)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(right_balance)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = (
                event.globalPosition().toPoint()
                - self.window_ref.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            self.drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self.window_ref.isMaximized()
        ):
            self.window_ref.move(
                event.globalPosition().toPoint() - self.drag_offset
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window_ref.toggle_maximize()
            event.accept()


class NavButton(QPushButton):
    def __init__(
        self,
        icon: str,
        text: str,
        page_id: str,
        active: bool = False,
    ) -> None:
        super().__init__(text)

        self.icon_kind = icon
        self.page_id = page_id
        self.setProperty("pageId", page_id)

        self.setObjectName("NavButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(62)
        self.setIconSize(QSize(20, 20))

        self.set_active(active)

    def set_active(self, active: bool) -> None:
        self.setProperty(
            "active",
            "true" if active else "false",
        )

        icon_color = "#27D3D1" if active else "#8395A2"

        self.setIcon(
            make_line_icon(
                self.icon_kind,
                icon_color,
                20,
            )
        )

        self.style().unpolish(self)
        self.style().polish(self)


class DeliveryButton(QPushButton):
    def __init__(self, text: str, icon: str) -> None:
        super().__init__(text)

        self.icon_kind = icon

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("DeliveryButton")
        self.setMinimumHeight(50)
        self.setIconSize(QSize(18, 18))

        self.toggled.connect(self._sync_icon)
        self._sync_icon(False)

    def _sync_icon(self, checked: bool) -> None:
        self.setIcon(
            make_line_icon(
                self.icon_kind,
                "#F7FFFF" if checked else "#A4B1BA",
                18,
            )
        )


class ReminderCard(QFrame):
    def __init__(
        self,
        row: Dict[str, str],
        language: str | None = None,
    ) -> None:
        super().__init__()
        language = language or runtime_language()
        self.setObjectName("ReminderCard")
        self.setMinimumHeight(124)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 14, 14, 14)
        outer.setSpacing(14)

        icon = QLabel()
        icon.setObjectName("ReminderIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(60, 60)
        icon.setPixmap(
            make_line_icon(
                "mail",
                "#27D3D1",
                25,
            ).pixmap(25, 25)
        )

        middle = QVBoxLayout()
        middle.setSpacing(3)

        run_at = parse_dt(row.get("next_run", ""))
        time_text = run_at.strftime("%H:%M") if run_at else "—"

        time_label = QLabel(time_text)
        time_label.setObjectName("ReminderTime")

        subject = (
            (row.get("subject") or "").strip()
            or ui_text("untitled_reminder", language)
        )
        subject_label = QLabel(subject)
        subject_label.setObjectName("ReminderSubject")
        subject_label.setWordWrap(True)

        tag = QLabel(
            channel_label("email", language)
        )
        tag.setObjectName("ChannelTag")
        tag.setFixedHeight(25)
        tag.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        middle.addWidget(time_label)
        middle.addWidget(subject_label)
        middle.addWidget(tag, alignment=Qt.AlignmentFlag.AlignLeft)

        more = QPushButton("⋮")
        more.setObjectName("MoreButton")
        more.setFixedSize(32, 36)
        more.setCursor(Qt.CursorShape.PointingHandCursor)
        more.setToolTip(
            ui_text("nav_reminders", language)
        )
        more.setAccessibleName(
            ui_text("nav_reminders", language)
        )

        body = (row.get("body") or "").strip()
        if body:
            self.setToolTip(body)

        outer.addWidget(icon)
        outer.addLayout(middle, 1)
        outer.addWidget(more, alignment=Qt.AlignmentFlag.AlignTop)


class InfoTile(QFrame):
    def __init__(self, icon: str, title: str, detail: str) -> None:
        super().__init__()
        self.setObjectName("InfoTile")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setObjectName("InfoIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(60, 60)
        icon_label.setPixmap(
            make_line_icon(
                icon,
                "#27D3D1",
                27,
            ).pixmap(27, 27)
        )

        texts = QVBoxLayout()
        texts.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("InfoTitle")
        title_label.setWordWrap(True)

        detail_label = QLabel(detail)
        detail_label.setObjectName("InfoDetail")
        detail_label.setWordWrap(True)

        texts.addWidget(title_label)
        texts.addWidget(detail_label)

        layout.addWidget(icon_label)
        layout.addLayout(texts, 1)


class PremiumWindow(QMainWindow):
    """Shared visual shell and reminder-composer foundation.

    Production page routing and data operations live in
    :mod:`hatirlatici_app`; advanced interactions, responsive behavior,
    tray handling, and the production entry point live in
    :mod:`hatirlatici_ultimate`.  This class deliberately owns only the
    reusable shell, controls, theme, and preview-safe CSV helpers.
    """

    def __init__(self) -> None:
        super().__init__()

        self.runtime_settings = runtime_config.load_settings()
        self.language = l10n.normalize_language(
            self.runtime_settings.get(
                "language",
                "en",
            )
        )

        configured_name = str(
            self.runtime_settings.get(
                "profile_name",
                "",
            )
            or ""
        ).strip()
        runtime_name = (
            runtime_config.profile_name()
        )
        profile_name = (
            runtime_name
            if configured_name
            else self._t("default_profile_name")
        )
        name_parts = profile_name.split()
        deduplicated_parts: list[str] = []
        for part in name_parts:
            if (
                deduplicated_parts
                and deduplicated_parts[-1].casefold()
                == part.casefold()
            ):
                continue
            deduplicated_parts.append(part)
        self.profile_name = (
            " ".join(deduplicated_parts)
            or self._t("default_profile_name")
        )

        configured_channel = str(
            self.runtime_settings.get(
                "default_channel",
                "email",
            )
        )
        self.default_channel = (
            configured_channel
            if configured_channel in CHANNEL_KEY_BY_VALUE
            else "email"
        )

        self.font_family = select_font()
        self.rows = load_rows()
        self.nav_buttons: List[NavButton] = []

        self.setWindowTitle(self._t("app_name"))
        self.setMinimumSize(960, 680)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        host = QWidget()
        host.setObjectName("Host")

        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(7, 7, 7, 7)
        host_layout.setSpacing(0)

        root = QFrame()
        root.setObjectName("Root")

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(TitleBar(self))

        body = QFrame()
        body.setObjectName("Body")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = self.build_sidebar()

        self.body_layout = body_layout
        self.main_widget = self.build_main()

        self.body_layout.addWidget(self.sidebar)
        self.body_layout.addWidget(
            self.main_widget,
            1,
        )

        root_layout.addWidget(body, 1)

        host_layout.addWidget(root)
        self.setCentralWidget(host)

        self.apply_styles()
        self.apply_visual_effects()

    def _t(
        self,
        key: str,
        **values: object,
    ) -> str:
        return ui_text(
            key,
            self.language,
            **values,
        )

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def build_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(270)

        layout = QVBoxLayout(side)
        layout.setContentsMargins(22, 28, 22, 20)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)

        brand_icon = QLabel()
        brand_icon.setObjectName("BrandIcon")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(42, 42)
        brand_icon.setPixmap(
            make_line_icon(
                "bell",
                "#27D3D1",
                24,
            ).pixmap(24, 24)
        )

        brand = QLabel(self._t("app_name"))
        brand.setObjectName("BrandText")

        brand_row.addWidget(brand_icon)
        brand_row.addWidget(brand)
        brand_row.addStretch(1)

        layout.addLayout(brand_row)
        layout.addSpacing(24)

        entries = [
            ("calendar", "today"),
            ("bell", "reminders"),
            ("history", "history"),
            ("settings", "settings"),
        ]

        for index, (icon, page_id) in enumerate(entries):
            btn = NavButton(
                icon,
                self._t(PAGE_LABEL_KEY[page_id]),
                page_id,
                active=index == 0,
            )
            btn.clicked.connect(
                lambda _checked=False, b=btn: self.activate_nav(b)
            )
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch(1)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(10)

        profile = QHBoxLayout()
        profile.setSpacing(10)

        initials = "".join(
            part[0]
            for part in self.profile_name.split()
            if part
        )[:2].upper() or "•"
        avatar = QLabel(initials)
        avatar.setObjectName("Avatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(44, 44)

        profile_text = QVBoxLayout()
        profile_text.setSpacing(2)

        name = QLabel(self.profile_name)
        name.setObjectName("ProfileName")
        name.setWordWrap(True)

        state = QLabel(self._t("profile_state"))
        state.setObjectName("ProfileState")
        state.setWordWrap(True)

        profile_text.addWidget(name)
        profile_text.addWidget(state)

        arrow = QLabel("›")
        arrow.setObjectName("ProfileArrow")

        profile.addWidget(avatar)
        profile.addLayout(profile_text, 1)
        profile.addWidget(arrow)

        layout.addLayout(profile)

        return side

    def activate_nav(self, selected: NavButton) -> None:
        for button in self.nav_buttons:
            button.set_active(button is selected)

        if selected.page_id != "today":
            self.preview_status.setText(
                self._t(PAGE_LABEL_KEY[selected.page_id])
            )
            QTimer.singleShot(2600, self.clear_preview_status)

    def active_today(self) -> List[Dict[str, str]]:
        today = dt.datetime.now().date()
        result: List[Dict[str, str]] = []

        for row in self.rows:
            if (row.get("enabled") or "").strip() != "1":
                continue

            run_at = parse_dt(row.get("next_run", ""))
            if run_at is not None and run_at.date() == today:
                result.append(row)

        result.sort(
            key=lambda row: parse_dt(row.get("next_run", ""))
            or dt.datetime.max
        )
        return result

    def active_upcoming(self) -> List[Dict[str, str]]:
        result = [
            row
            for row in self.rows
            if (row.get("enabled") or "").strip() == "1"
            and parse_dt(row.get("next_run", "")) is not None
        ]

        result.sort(
            key=lambda row: parse_dt(row.get("next_run", ""))
            or dt.datetime.max
        )
        return result

    def build_main(self) -> QFrame:
        main = QFrame()
        main.setObjectName("Main")

        layout = QVBoxLayout(main)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)

        layout.addLayout(self.build_header())

        columns = QHBoxLayout()
        columns.setSpacing(22)
        self.dashboard_columns = columns

        form_card = self.build_form_card()
        today_card = self.build_today_card()

        columns.addWidget(form_card, 57)
        columns.addWidget(today_card, 43)

        layout.addLayout(columns, 1)
        layout.addWidget(self.build_info_strip())

        return main

    def build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(3)

        safe_name = html.escape(
            self.profile_name,
            quote=True,
        )
        greeting = QLabel(
            self._t(
                "greeting",
                name=(
                    '<span style="color:#27D3D1;">'
                    f"{safe_name}</span>"
                ),
            )
        )
        greeting.setObjectName("Greeting")
        greeting.setTextFormat(Qt.TextFormat.RichText)
        greeting.setWordWrap(True)
        greeting.setMinimumWidth(0)
        greeting.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )

        today_count = len(self.active_today())
        if today_count:
            sub_text = localized_today_count(
                today_count,
                self.language,
            )
        else:
            sub_text = self._t("today_none")

        sub = QLabel(sub_text)
        sub.setObjectName("GreetingSub")
        sub.setWordWrap(True)
        sub.setMinimumWidth(0)

        texts.addWidget(greeting)
        texts.addWidget(sub)

        new_button = QPushButton(
            "＋  " + self._t("new_reminder")
        )
        new_button.setObjectName("PrimaryTopButton")
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_button.setMinimumSize(190, 54)
        new_button.setMaximumWidth(310)
        new_button.clicked.connect(self.focus_new_reminder)

        header.addLayout(texts)
        header.addStretch(1)
        header.addWidget(
            new_button,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        return header

    def build_form_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(11)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("SectionIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(46, 46)
        icon.setPixmap(
            make_line_icon(
                "calendar_plus",
                "#27D3D1",
                24,
            ).pixmap(24, 24)
        )

        title = QLabel(self._t("new_reminder"))
        title.setObjectName("SectionTitle")

        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch(1)

        layout.addLayout(title_row)
        layout.addSpacing(4)

        label = QLabel(self._t("subject_label"))
        label.setObjectName("FieldLabel")
        layout.addWidget(label)

        self.subject_edit = QLineEdit()
        self.subject_edit.setObjectName("TextInput")
        self.subject_edit.setPlaceholderText(
            self._t("subject_placeholder")
        )
        self.subject_edit.setMinimumHeight(50)
        layout.addWidget(self.subject_edit)

        layout.addSpacing(5)

        datetime_row = QHBoxLayout()
        datetime_row.setSpacing(16)

        date_column = QVBoxLayout()
        date_column.setSpacing(6)

        date_label = QLabel(self._t("date"))
        date_label.setObjectName("FieldLabel")

        self.date_edit = QDateEdit()
        self.date_edit.setObjectName("DateInput")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setLocale(
            qt_locale(self.language)
        )
        self.date_edit.setDisplayFormat("dd MMMM yyyy")
        self.date_edit.setMinimumHeight(50)

        time_column = QVBoxLayout()
        time_column.setSpacing(6)

        time_label = QLabel(self._t("time"))
        time_label.setObjectName("FieldLabel")

        self.time_edit = QTimeEdit()
        self.time_edit.setObjectName("TimeInput")
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setMinimumHeight(50)

        future = dt.datetime.now() + dt.timedelta(minutes=10)
        self.date_edit.setDate(
            QDate(future.year, future.month, future.day)
        )
        self.time_edit.setTime(
            QTime(future.hour, future.minute)
        )

        date_column.addWidget(date_label)
        date_column.addWidget(self.date_edit)

        time_column.addWidget(time_label)
        time_column.addWidget(self.time_edit)

        datetime_row.addLayout(date_column, 1)
        datetime_row.addLayout(time_column, 1)

        layout.addLayout(datetime_row)
        layout.addSpacing(5)

        repeat_label = QLabel(self._t("repeat"))
        repeat_label.setObjectName("FieldLabel")
        layout.addWidget(repeat_label)

        self.repeat_combo = QComboBox()
        self.repeat_combo.setObjectName("ComboInput")
        self.repeat_combo.setMinimumHeight(50)
        for repeat_value in REPEAT_KEY_BY_VALUE:
            self.repeat_combo.addItem(
                localized_repeat(
                    repeat_value,
                    self.language,
                ),
                repeat_value,
            )
        layout.addWidget(self.repeat_combo)

        layout.addSpacing(5)

        method_label = QLabel(self._t("reminder_method"))
        method_label.setObjectName("FieldLabel")
        layout.addWidget(method_label)

        method_frame = QFrame()
        method_frame.setObjectName("DeliveryFrame")
        method_layout = QHBoxLayout(method_frame)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(0)

        self.delivery_group = QButtonGroup(self)
        self.delivery_group.setExclusive(True)

        mail_button = DeliveryButton(
            self._t("delivery_email"),
            "mail",
        )
        pc_button = DeliveryButton(
            self._t("delivery_pc"),
            "monitor",
        )
        both_button = DeliveryButton(
            self._t("delivery_both"),
            "both",
        )

        for index, (button, channel) in enumerate(
            (
                (mail_button, "email"),
                (pc_button, "pc"),
                (both_button, "both"),
            )
        ):
            button.setProperty("channel", channel)
            self.delivery_group.addButton(button, index)
            method_layout.addWidget(button, 1)

            if channel == self.default_channel:
                button.setChecked(True)

        self.delivery_group.buttonClicked.connect(
            self.delivery_changed
        )

        layout.addWidget(method_frame)

        self.channel_info = QLabel(
            "ⓘ   "
            + self._t(
                "channel_selected",
                channel=channel_label(
                    self.default_channel,
                    self.language,
                ),
            )
        )
        self.channel_info.setObjectName("InlineInfo")
        self.channel_info.setMinimumHeight(38)
        self.channel_info.setWordWrap(True)
        layout.addWidget(self.channel_info)

        layout.addSpacing(4)

        note_label = QLabel(self._t("note"))
        note_label.setProperty("fieldRole", "note")
        note_label.setObjectName("FieldLabel")
        layout.addWidget(note_label)

        self.note_edit = QTextEdit()
        self.note_edit.setObjectName("NoteInput")
        self.note_edit.setPlaceholderText(
            self._t("note_placeholder")
        )
        self.note_edit.setMinimumHeight(92)
        self.note_edit.setMaximumHeight(112)
        layout.addWidget(self.note_edit)

        layout.addStretch(1)

        save = QPushButton(
            "✓   " + self._t("save_reminder")
        )
        save.setObjectName("SaveButton")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setMinimumHeight(56)
        save.clicked.connect(self.preview_save)
        layout.addWidget(save)

        self.preview_status = QLabel("")
        self.preview_status.setObjectName("PreviewStatus")
        self.preview_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_status.setMinimumHeight(22)
        layout.addWidget(self.preview_status)

        return card

    def build_system_summary(self) -> QFrame:
        active_count = 0
        total_sends = 0
        last_sent_values = []

        for row in self.rows:
            if (row.get("enabled") or "").strip() == "1":
                active_count += 1

            try:
                total_sends += int(
                    (row.get("send_count") or "0").strip()
                )
            except ValueError:
                pass

            sent = parse_dt(row.get("last_sent", ""))
            if sent is not None:
                last_sent_values.append(sent)

        if last_sent_values:
            latest = max(last_sent_values)
            latest_text = latest.strftime("%d.%m • %H:%M")
        else:
            latest_text = self._t("none_yet")

        card = QFrame()
        card.setObjectName("SystemSummary")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 15, 17, 15)
        layout.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(9)

        icon = QLabel()
        icon.setPixmap(
            make_line_icon(
                "local",
                "#27D3D1",
                20,
            ).pixmap(20, 20)
        )

        title = QLabel(self._t("system_summary"))
        title.setObjectName("SystemSummaryTitle")

        pill = QLabel(self._t("system_status"))
        pill.setObjectName("SystemLivePill")

        head.addWidget(icon)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(pill)

        layout.addLayout(head)

        stats = QHBoxLayout()
        stats.setSpacing(8)

        data = (
            (self._t("stat_active"), str(active_count)),
            (self._t("stat_deliveries"), str(total_sends)),
            (self._t("stat_last_delivery"), latest_text),
        )

        for label_text, value_text in data:
            cell = QFrame()
            cell.setObjectName("StatCell")

            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(10, 9, 10, 9)
            cell_layout.setSpacing(2)

            value = QLabel(value_text)
            value.setObjectName("StatValue")

            label = QLabel(label_text)
            label.setObjectName("StatLabel")
            label.setWordWrap(True)
            label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            cell_layout.addWidget(value)
            cell_layout.addWidget(label)

            stats.addWidget(cell, 1)

        layout.addLayout(stats)

        return card

    def build_today_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 24, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()

        left = QHBoxLayout()
        left.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(
            make_line_icon(
                "calendar",
                "#EAF4F8",
                20,
            ).pixmap(20, 20)
        )
        icon.setObjectName("SmallHeaderIcon")

        title = QLabel(self._t("nav_today"))
        title.setObjectName("SectionTitle")

        left.addWidget(icon)
        left.addWidget(title)

        all_button = QPushButton(
            self._t("view_all") + "   ›"
        )
        all_button.setObjectName("SecondaryButton")
        all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        all_button.setFixedHeight(38)
        all_button.clicked.connect(
            lambda: self.show_status(
                self._t("nav_reminders")
            )
        )

        header.addLayout(left)
        header.addStretch(1)
        header.addWidget(all_button)

        layout.addLayout(header)
        layout.addSpacing(3)

        today_rows = self.active_today()
        visible = today_rows[:3]

        if not visible:
            upcoming = self.active_upcoming()
            visible = upcoming[:3]

        if visible:
            for row in visible:
                layout.addWidget(
                    ReminderCard(
                        row,
                        self.language,
                    )
                )

            if len(visible) < 3:
                quiet = QFrame()
                quiet.setObjectName("QuietState")

                quiet_layout = QVBoxLayout(quiet)
                quiet_layout.setContentsMargins(18, 20, 18, 20)
                quiet_layout.setSpacing(6)

                quiet_icon = QLabel("✓")
                quiet_icon.setObjectName("QuietIcon")
                quiet_icon.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                quiet_title = QLabel(
                    self._t("today_no_more")
                )
                quiet_title.setObjectName("QuietTitle")
                quiet_title.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                quiet_detail = QLabel(
                    self._t("reminders_appear_here")
                )
                quiet_detail.setObjectName("QuietDetail")
                quiet_detail.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                quiet_detail.setWordWrap(True)

                quiet_layout.addWidget(quiet_icon)
                quiet_layout.addWidget(quiet_title)
                quiet_layout.addWidget(quiet_detail)

                layout.addWidget(quiet)
        else:
            empty = QFrame()
            empty.setObjectName("EmptyState")

            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(20, 28, 20, 28)

            empty_icon = QLabel("✓")
            empty_icon.setObjectName("EmptyIcon")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

            empty_title = QLabel(
                self._t("empty_calm")
            )
            empty_title.setObjectName("EmptyTitle")
            empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            empty_detail = QLabel(
                self._t("active_appear_here")
            )
            empty_detail.setObjectName("EmptyDetail")
            empty_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_detail.setWordWrap(True)

            empty_layout.addWidget(empty_icon)
            empty_layout.addWidget(empty_title)
            empty_layout.addWidget(empty_detail)

            layout.addWidget(empty)

        if len(visible) < 3:
            layout.addWidget(
                self.build_system_summary()
            )

        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName("RightFooter")

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 10, 14, 10)
        footer_layout.setSpacing(10)

        footer_icon = QLabel()
        footer_icon.setObjectName("FooterIcon")
        footer_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_icon.setFixedSize(38, 38)
        footer_icon.setPixmap(
            make_line_icon(
                "bell",
                "#27D3D1",
                20,
            ).pixmap(20, 20)
        )

        footer_text = QLabel(
            self._t("channels_independent")
        )
        footer_text.setObjectName("FooterText")
        footer_text.setWordWrap(True)

        screen_icon = QLabel()
        screen_icon.setObjectName("FooterScreen")
        screen_icon.setPixmap(
            make_line_icon(
                "monitor",
                "#27D3D1",
                25,
            ).pixmap(25, 25)
        )

        footer_layout.addWidget(footer_icon)
        footer_layout.addWidget(footer_text, 1)
        footer_layout.addWidget(screen_icon)

        layout.addWidget(footer)

        return card

    def build_info_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("InfoStrip")
        strip.setFixedHeight(116)

        layout = QHBoxLayout(strip)
        self.info_strip = strip
        self.info_strip_layout = layout
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)

        layout.addWidget(
            InfoTile(
                "mail",
                self._t("info_email_title"),
                self._t("info_email_detail"),
            ),
            1,
        )

        layout.addWidget(
            InfoTile(
                "monitor",
                self._t("info_desktop_title"),
                self._t("info_desktop_detail"),
            ),
            1,
        )

        layout.addWidget(
            InfoTile(
                "local",
                self._t("info_local_title"),
                self._t("info_local_detail"),
            ),
            1,
        )

        return strip

    def focus_new_reminder(self) -> None:
        self.subject_edit.setFocus()
        self.subject_edit.selectAll()

    def delivery_changed(self, button: QPushButton) -> None:
        channel = str(
            button.property("channel")
            or "email"
        )
        message = self._t(
            "channel_selected",
            channel=channel_label(
                channel,
                self.language,
            ),
        )
        self.channel_info.setText(
            "ⓘ   " + message
        )
        self.show_status(message)

    def _refresh_main_after_save(
        self,
        message: str,
    ) -> None:
        self.rows = load_rows()

        old_main = self.main_widget
        new_main = self.build_main()

        self.body_layout.replaceWidget(
            old_main,
            new_main,
        )

        old_main.deleteLater()

        self.main_widget = new_main

        # QSS global olduğu için yeni widget'lar otomatik
        # olarak aynı görsel sistemi alır.
        # Sadece statik derinlik efektlerini yeniden uygula.
        for frame in new_main.findChildren(QFrame):
            if frame.objectName() not in {
                "Card",
                "InfoStrip",
            }:
                continue

            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(32)
            shadow.setOffset(0, 9)
            shadow.setColor(
                QColor(0, 0, 0, 125)
            )
            frame.setGraphicsEffect(shadow)

        for button in new_main.findChildren(
            QPushButton
        ):
            if button.objectName() not in {
                "PrimaryTopButton",
                "SaveButton",
            }:
                continue

            glow = QGraphicsDropShadowEffect(button)
            glow.setBlurRadius(22)
            glow.setOffset(0, 4)
            glow.setColor(
                QColor(39, 211, 209, 48)
            )
            button.setGraphicsEffect(glow)

        self.preview_status.setText(message)

        QTimer.singleShot(
            4500,
            self.clear_preview_status,
        )

    def preview_save(self) -> None:
        channel_id = (
            self.delivery_group.checkedId()
        )

        # The standalone preview writer supports its historical email CSV
        # contract only.  Production multi-channel writes live in core_v2.
        if channel_id != 0:
            self.show_status(
                self._t("preview_save_blocked")
            )
            return

        subject = self.subject_edit.text().strip()

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

        repeat_value = (
            self.repeat_combo.currentData()
        )

        if repeat_value is None:
            self.show_status(
                self._t("invalid_repeat")
            )
            return

        body = (
            self.note_edit
            .toPlainText()
            .strip()
        )

        try:
            reminder_id = append_email_reminder(
                CSV_PATH,
                subject,
                body,
                run_at,
                repeat_value,
            )

        except ValueError as exc:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t(
                        "operation_failed_detail"
                    ),
                )
            )
            return

        except Exception as exc:
            self.show_status(
                self._t(
                    "save_failed",
                    error=self._t(
                        "operation_failed_detail"
                    ),
                )
            )
            return

        self._refresh_main_after_save(
            "✓ "
            + self._t(
                "reminder_saved",
                channel=channel_label(
                    "email",
                    self.language,
                ),
            )
            + f" • ID {reminder_id}"
        )

    def show_status(self, text: str) -> None:
        self.preview_status.setText(text)
        QTimer.singleShot(3200, self.clear_preview_status)

    def clear_preview_status(self) -> None:
        self.preview_status.setText("")

    def apply_visual_effects(self) -> None:
        # Second-layer style overrides.
        # This keeps the original design system intact and makes
        # visual refinement easier to audit/revert.
        self.setStyleSheet(
            self.styleSheet()
            + """
            QLabel#BrandText {
                font-size: 22px;
                font-weight: 750;
            }

            QPushButton#NavButton {
                font-size: 15px;
            }

            QLabel#Greeting {
                font-size: 32px;
                font-weight: 800;
            }

            QLabel#GreetingSub {
                font-size: 14px;
            }

            QLabel#SectionTitle {
                font-size: 20px;
                font-weight: 750;
            }

            QLabel#FieldLabel {
                font-size: 13px;
            }

            QLineEdit#TextInput,
            QDateEdit#DateInput,
            QTimeEdit#TimeInput,
            QComboBox#ComboInput,
            QTextEdit#NoteInput {
                font-size: 14px;
            }

            QPushButton#PrimaryTopButton,
            QPushButton#SaveButton {
                font-size: 15px;
                font-weight: 750;
                border-radius: 11px;
            }

            QFrame#Card {
                border: 1px solid #304552;
                border-radius: 16px;
            }

            QFrame#ReminderCard {
                border: 1px solid #304653;
                border-left: 3px solid #27D3D1;
                border-radius: 12px;
            }

            QLabel#ReminderTime {
                font-size: 19px;
                font-weight: 750;
            }

            QLabel#ReminderSubject {
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#ChannelTag {
                font-size: 11px;
                padding: 3px 9px;
            }

            QLabel#InlineInfo {
                font-size: 12px;
            }

            QFrame#QuietState {
                background: #0B151E;
                border: 1px dashed #29414D;
                border-radius: 12px;
                min-height: 106px;
            }

            QLabel#QuietIcon {
                color: #27D3D1;
                font-size: 23px;
                font-weight: 750;
            }

            QLabel#QuietTitle {
                color: #D0DCE2;
                font-size: 13px;
                font-weight: 650;
            }

            QLabel#QuietDetail {
                color: #788996;
                font-size: 11px;
            }

            QFrame#InfoStrip {
                border: 1px solid #2B4A54;
                border-radius: 14px;
            }

            QLabel#InfoTitle {
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#InfoDetail {
                font-size: 11px;
            }

            QLabel#FooterText {
                font-size: 11px;
            }
            """
        )

        self.setStyleSheet(
            self.styleSheet()
            + """
            QFrame#SystemSummary {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0E1A23,
                    stop:1 #0A141C
                );
                border: 1px solid #29414D;
                border-radius: 12px;
            }

            QLabel#SystemSummaryTitle {
                color: #DCE8ED;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#SystemLivePill {
                color: #27D3D1;
                background: rgba(39, 211, 209, 0.07);
                border: 1px solid #176A71;
                border-radius: 5px;
                padding: 3px 7px;
                font-size: 11px;
                font-weight: 700;
            }

            QFrame#StatCell {
                background: #09131B;
                border: 1px solid #213641;
                border-radius: 8px;
            }

            QLabel#StatValue {
                color: #EDF6F8;
                font-size: 13px;
                font-weight: 750;
            }

            QLabel#StatLabel {
                color: #738591;
                font-size: 11px;
            }

            QPushButton#NavButton {
                padding-left: 19px;
                text-align: left;
            }

            QPushButton#DeliveryButton {
                padding-left: 8px;
                padding-right: 8px;
            }
            """
        )

        self.setStyleSheet(
            self.styleSheet()
            + """
            QWidget#LeftWindowControls,
            QWidget#RightTitleBalance {
                background: transparent;
                border: none;
            }

            QPushButton#WindowControl {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid transparent;
                border-radius: 7px;
                color: #8EA0AC;
                font-size: 15px;
                font-weight: 650;
                padding: 0px;
            }

            QPushButton#WindowControl:hover {
                background: #17232D;
                border-color: #314550;
                color: #F5FAFC;
            }

            QPushButton#WindowControl:pressed {
                background: #21323D;
                border-color: #3A5662;
            }

            QPushButton#WindowControl[danger="true"] {
                color: #AEBBC3;
            }

            QPushButton#WindowControl[danger="true"]:hover {
                background: #A73A46;
                border-color: #D25C65;
                color: #FFFFFF;
            }

            QLabel#TitleMark {
                background: rgba(39, 211, 209, 0.055);
                border: 1px solid #174F56;
                border-radius: 15px;
            }

            QLabel#WindowTitle {
                color: #DDE7EC;
                font-size: 13px;
                font-weight: 650;
            }
            """
        )

        # Static depth only: no timers, no continuous animation,
        # no unnecessary CPU/GPU load.
        for frame in self.findChildren(QFrame):
            if frame.objectName() not in {"Card", "InfoStrip"}:
                continue

            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(32)
            shadow.setOffset(0, 9)
            shadow.setColor(QColor(0, 0, 0, 125))
            frame.setGraphicsEffect(shadow)

        for button in self.findChildren(QPushButton):
            if button.objectName() not in {
                "PrimaryTopButton",
                "SaveButton",
            }:
                continue

            glow = QGraphicsDropShadowEffect(button)
            glow.setBlurRadius(22)
            glow.setOffset(0, 4)
            glow.setColor(QColor(39, 211, 209, 48))
            button.setGraphicsEffect(glow)

    def apply_styles(self) -> None:
        f = self.font_family

        self.setStyleSheet(
            f"""
            * {{
                font-family: "{f}";
                color: {COLORS["text"]};
                outline: none;
            }}

            QWidget#Host {{
                background: transparent;
            }}

            QFrame#Root {{
                background: {COLORS["root"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 16px;
            }}

            QFrame#TitleBar {{
                background: #060A0F;
                border: none;
                border-bottom: 1px solid #19242E;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}

            QLabel#TitleMark {{
                color: {COLORS["accent"]};
                font-size: 13px;
            }}

            QLabel#WindowTitle {{
                font-size: 14px;
                font-weight: 600;
                color: #D9E5EC;
            }}

            QPushButton#WindowControl {{
                background: transparent;
                border: none;
                color: #A8B5C0;
                font-size: 17px;
                border-radius: 7px;
            }}

            QPushButton#WindowControl:hover {{
                background: #17212B;
                color: white;
            }}

            QPushButton#WindowControl[danger="true"]:hover {{
                background: #B83A45;
                color: white;
            }}

            QFrame#Body {{
                background: transparent;
                border: none;
            }}

            QFrame#Sidebar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #071018,
                    stop:1 #0A121A
                );
                border: none;
                border-right: 1px solid #17232E;
                border-bottom-left-radius: 16px;
            }}

            QLabel#BrandIcon {{
                background: rgba(39, 211, 209, 0.08);
                border: 1px solid #176D73;
                border-radius: 21px;
                color: {COLORS["accent"]};
                font-size: 22px;
            }}

            QLabel#BrandText {{
                font-size: 20px;
                font-weight: 700;
                color: #F4F8FA;
            }}

            QPushButton#NavButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
                padding: 0 18px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                color: #A6B2BD;
            }}

            QPushButton#NavButton:hover {{
                background: #101B25;
                color: #E9F4F7;
            }}

            QPushButton#NavButton[active="true"] {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(25, 113, 123, 0.42),
                    stop:1 rgba(20, 53, 64, 0.55)
                );
                border: 1px solid #1D6972;
                color: {COLORS["accent"]};
                font-weight: 650;
            }}

            QFrame#SidebarDivider {{
                background: #26333E;
                border: none;
            }}

            QLabel#Avatar {{
                background: #111D28;
                border: 1px solid #36505E;
                border-radius: 22px;
                color: {COLORS["accent"]};
                font-size: 12px;
                font-weight: 700;
            }}

            QLabel#ProfileName {{
                color: #CFD9E0;
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#ProfileState {{
                color: {COLORS["accent"]};
                font-size: 11px;
            }}

            QLabel#ProfileArrow {{
                color: #AAB7C1;
                font-size: 25px;
            }}

            QFrame#Main {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #091017,
                    stop:0.55 #0A121A,
                    stop:1 #080E14
                );
                border: none;
                border-bottom-right-radius: 16px;
            }}

            QLabel#Greeting {{
                font-size: 27px;
                font-weight: 750;
                color: white;
            }}

            QLabel#GreetingSub {{
                font-size: 13px;
                color: {COLORS["muted"]};
            }}

            QPushButton#PrimaryTopButton,
            QPushButton#SaveButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #24C9CB,
                    stop:1 #118D9D
                );
                border: 1px solid #42E1DE;
                color: #F9FFFF;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}

            QPushButton#PrimaryTopButton:hover,
            QPushButton#SaveButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #36DDDB,
                    stop:1 #16A6B6
                );
                border-color: #72F0EC;
            }}

            QPushButton#PrimaryTopButton:pressed,
            QPushButton#SaveButton:pressed {{
                background: #118894;
            }}

            QFrame#Card {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0E1720,
                    stop:1 #0B131B
                );
                border: 1px solid #263543;
                border-radius: 14px;
            }}

            QLabel#SectionIcon {{
                background: rgba(39, 211, 209, 0.08);
                border: 1px solid #155F66;
                border-radius: 23px;
                color: {COLORS["accent"]};
                font-size: 16px;
                font-weight: 600;
            }}

            QLabel#SectionTitle {{
                font-size: 18px;
                font-weight: 700;
                color: #F2F7FA;
            }}

            QLabel#SmallHeaderIcon {{
                color: #EAF4F8;
                font-size: 18px;
            }}

            QLabel#FieldLabel {{
                font-size: 12px;
                font-weight: 500;
                color: #AAB6C1;
            }}

            QLineEdit#TextInput,
            QDateEdit#DateInput,
            QTimeEdit#TimeInput,
            QComboBox#ComboInput,
            QTextEdit#NoteInput {{
                background: #0A121B;
                border: 1px solid #30404F;
                border-radius: 8px;
                color: #DDE6EC;
                padding: 0 13px;
                font-size: 13px;
                selection-background-color: #137984;
            }}

            QTextEdit#NoteInput {{
                padding: 10px 13px;
            }}

            QLineEdit#TextInput:hover,
            QDateEdit#DateInput:hover,
            QTimeEdit#TimeInput:hover,
            QComboBox#ComboInput:hover,
            QTextEdit#NoteInput:hover {{
                border-color: #3E5666;
                background: #0D1721;
            }}

            QLineEdit#TextInput:focus,
            QDateEdit#DateInput:focus,
            QTimeEdit#TimeInput:focus,
            QComboBox#ComboInput:focus,
            QTextEdit#NoteInput:focus {{
                border: 1px solid {COLORS["accent"]};
                background: #0D1822;
            }}

            QComboBox#ComboInput::drop-down,
            QDateEdit#DateInput::drop-down,
            QTimeEdit#TimeInput::drop-down {{
                border: none;
                width: 32px;
            }}

            QComboBox QAbstractItemView {{
                background: #101A24;
                border: 1px solid #30404F;
                color: #E6EFF4;
                selection-background-color: #116D77;
                padding: 6px;
            }}

            QFrame#DeliveryFrame {{
                background: #0A121A;
                border: 1px solid #2B3A47;
                border-radius: 8px;
            }}

            QPushButton#DeliveryButton {{
                background: transparent;
                border: none;
                border-right: 1px solid #263743;
                color: #B7C2CB;
                font-size: 12px;
                font-weight: 600;
            }}

            QPushButton#DeliveryButton:hover {{
                background: #11212A;
                color: white;
            }}

            QPushButton#DeliveryButton:checked {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1EBEC2,
                    stop:1 #128B99
                );
                color: white;
                border: 1px solid #35D9D7;
            }}

            QLabel#InlineInfo {{
                background: #0A141C;
                border: 1px solid #223540;
                border-radius: 7px;
                padding: 0 11px;
                color: #8FA1AE;
                font-size: 11px;
            }}

            QLabel#PreviewStatus {{
                color: #69D9D5;
                font-size: 11px;
            }}

            QPushButton#SecondaryButton {{
                background: #0E1720;
                border: 1px solid #30404D;
                border-radius: 8px;
                color: #B6C2CB;
                padding: 0 13px;
                font-size: 11px;
            }}

            QPushButton#SecondaryButton:hover {{
                border-color: #3D6870;
                color: white;
                background: #12202A;
            }}

            QFrame#ReminderCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #101B25,
                    stop:1 #0D1720
                );
                border: 1px solid #293A48;
                border-left: 2px solid {COLORS["accent"]};
                border-radius: 11px;
            }}

            QLabel#ReminderIcon {{
                background: rgba(39, 211, 209, 0.06);
                border: 1px solid #14656D;
                border-radius: 27px;
                color: {COLORS["accent"]};
                font-size: 23px;
            }}

            QLabel#ReminderTime {{
                color: {COLORS["accent"]};
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#ReminderSubject {{
                color: #F0F5F7;
                font-size: 13px;
                font-weight: 650;
            }}

            QLabel#ChannelTag {{
                color: {COLORS["accent"]};
                background: transparent;
                border: 1px solid #15818A;
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
            }}

            QPushButton#MoreButton {{
                background: transparent;
                border: none;
                color: #92A2AE;
                font-size: 20px;
            }}

            QPushButton#MoreButton:hover {{
                color: white;
                background: #17232D;
                border-radius: 7px;
            }}

            QFrame#EmptyState {{
                background: #0B141C;
                border: 1px dashed #263B47;
                border-radius: 10px;
            }}

            QLabel#EmptyIcon {{
                color: {COLORS["accent"]};
                font-size: 30px;
            }}

            QLabel#EmptyTitle {{
                color: #DCE8ED;
                font-size: 14px;
                font-weight: 650;
            }}

            QLabel#EmptyDetail {{
                color: #81909D;
                font-size: 11px;
            }}

            QFrame#RightFooter {{
                background: #0A141C;
                border: 1px solid #273945;
                border-radius: 9px;
            }}

            QLabel#FooterIcon {{
                color: {COLORS["accent"]};
                background: rgba(39, 211, 209, 0.05);
                border: 1px solid #1B5F66;
                border-radius: 19px;
                font-size: 17px;
            }}

            QLabel#FooterText {{
                color: #9DAAB5;
                font-size: 11px;
            }}

            QLabel#FooterScreen {{
                color: {COLORS["accent"]};
                font-size: 25px;
            }}

            QFrame#InfoStrip {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0B151E,
                    stop:0.5 #0E1822,
                    stop:1 #0A141C
                );
                border: 1px solid #25404A;
                border-radius: 13px;
            }}

            QFrame#InfoTile {{
                background: transparent;
                border: none;
            }}

            QLabel#InfoIcon {{
                color: {COLORS["accent"]};
                background: rgba(39, 211, 209, 0.05);
                border: 1px solid #14626B;
                border-radius: 27px;
                font-size: 23px;
            }}

            QLabel#InfoTitle {{
                color: #E7EEF2;
                font-size: 12px;
                font-weight: 650;
            }}

            QLabel#InfoDetail {{
                color: #8A99A5;
                font-size: 11px;
            }}

            QToolTip {{
                background: #111B24;
                color: white;
                border: 1px solid #32505A;
                padding: 6px;
            }}
            """
        )
