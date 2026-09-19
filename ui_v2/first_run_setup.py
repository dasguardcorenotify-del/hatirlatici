#!/usr/bin/env python3
"""Final first-launch setup for the public Hatırlatıcı application.

Earlier experimental runtime class installers were removed. Responsive
layout, language switching, skipped steps and secure credential handling now
live in one production dialog.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "ui_v2"
for candidate in (ROOT, UI_ROOT):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)


from PyQt6.QtCore import QLocale, QRectF, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import credential_vault
import l10n
import runtime_config
import setup_model
import setup_persistence
from language_menu import LanguageMenuButton


GOOGLE_2SV_URL = (
    "https://myaccount.google.com/signinoptions/two-step-verification"
)
GOOGLE_APP_PASSWORDS_URL = "https://myaccount.google.com/apppasswords"


def _line_icon(kind: str, size: int = 28) -> QIcon:
    """Render a small dependency-free, self-owned line icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor("#43D6DC"))
    pen.setWidthF(max(1.6, size * 0.075))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    s = float(size)

    if kind == "monitor":
        painter.drawRoundedRect(QRectF(s * .12, s * .15, s * .76, s * .55), 3, 3)
        painter.drawLine(int(s * .50), int(s * .70), int(s * .50), int(s * .84))
        painter.drawLine(int(s * .34), int(s * .85), int(s * .66), int(s * .85))
    elif kind == "mail":
        painter.drawRoundedRect(QRectF(s * .11, s * .22, s * .78, s * .57), 3, 3)
        painter.drawLine(int(s * .14), int(s * .28), int(s * .50), int(s * .54))
        painter.drawLine(int(s * .86), int(s * .28), int(s * .50), int(s * .54))
    elif kind == "both":
        painter.drawRoundedRect(QRectF(s * .08, s * .14, s * .57, s * .40), 3, 3)
        painter.drawLine(int(s * .10), int(s * .18), int(s * .36), int(s * .38))
        painter.drawLine(int(s * .62), int(s * .18), int(s * .36), int(s * .38))
        painter.drawRoundedRect(QRectF(s * .42, s * .48, s * .50, s * .36), 3, 3)
        painter.drawLine(int(s * .67), int(s * .84), int(s * .67), int(s * .91))
    elif kind == "gmail":
        painter.drawRoundedRect(QRectF(s * .10, s * .22, s * .80, s * .57), 3, 3)
        painter.drawLine(int(s * .12), int(s * .26), int(s * .50), int(s * .55))
        painter.drawLine(int(s * .88), int(s * .26), int(s * .50), int(s * .55))
    elif kind == "server":
        for y in (.17, .43, .69):
            painter.drawRoundedRect(QRectF(s * .13, s * y, s * .74, s * .19), 2, 2)
            painter.drawPoint(int(s * .22), int(s * (y + .095)))
    painter.end()
    return QIcon(pixmap)


class ChoiceCard(QFrame):
    """Selectable delivery/provider card with full keyboard operation."""

    chosen = pyqtSignal(str)

    def __init__(self, value: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.value = value
        self.setObjectName("choiceCard")
        self.setProperty("selected", False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(142)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 15, 17, 15)
        layout.setSpacing(7)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("choiceIcon")
        self.icon_label.setPixmap(_line_icon(icon_name, 30).pixmap(30, 30))
        self.icon_label.setFixedSize(34, 34)
        self.title_label = QLabel()
        self.title_label.setObjectName("choiceTitle")
        self.title_label.setWordWrap(True)
        self.description_label = QLabel()
        self.description_label.setObjectName("choiceDescription")
        self.description_label.setWordWrap(True)
        for label in (self.icon_label, self.title_label, self.description_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)
        layout.addStretch(1)

    def set_copy(self, title: str, description: str) -> None:
        self.title_label.setText(title)
        self.description_label.setText(description)
        self.setAccessibleName(f"{title}. {description}")

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.chosen.emit(self.value)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.chosen.emit(self.value)
            event.accept()
            return
        super().keyPressEvent(event)


class NoticeDialog(QDialog):
    """Consistent in-product validation and information notice."""

    def __init__(self, parent: QWidget, title: str, message: str, button_text: str) -> None:
        super().__init__(parent)
        self.setObjectName("noticeDialog")
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setMaximumWidth(620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("noticeTitle")
        heading.setWordWrap(True)
        body = QLabel(message)
        body.setObjectName("noticeBody")
        body.setWordWrap(True)
        close_button = QPushButton(button_text)
        close_button.setObjectName("primaryButton")
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addLayout(row)


class GuidedFirstRunDialog(QDialog):
    """The single final five-step first-run implementation."""

    GOOGLE_2SV_URL = GOOGLE_2SV_URL
    GOOGLE_APP_PASSWORDS_URL = GOOGLE_APP_PASSWORDS_URL

    def __init__(self, *, force: bool = False, preview: bool = False) -> None:
        super().__init__()
        self.force = force
        self.preview = preview
        self._settings = runtime_config.load_settings()
        existing_language = str(self._settings.get("language", "")).strip().lower()
        if existing_language in l10n.SUPPORTED_LANGUAGES:
            initial_language = existing_language
        else:
            system_language = QLocale.system().name().split("_", 1)[0].lower()
            initial_language = system_language if system_language in l10n.SUPPORTED_LANGUAGES else "en"
        channel = str(self._settings.get("default_channel", "pc")).strip().lower()
        provider = str(self._settings.get("smtp_provider", "gmail")).strip().lower()
        self.selected_channel = channel if channel in setup_model.CHANNELS else "pc"
        self.selected_provider = provider if provider in setup_model.PROVIDERS else "gmail"
        self.language = initial_language

        self.setObjectName("guidedFirstRun")
        self.setMinimumSize(960, 680)
        self.resize(1000, 700)
        self._build_ui()
        self._load_existing()
        self.language_selector.select_language(initial_language, emit=False)
        self._set_channel(self.selected_channel)
        self._set_provider(self.selected_provider)
        self._apply_language(initial_language)
        self.pages.setCurrentIndex(0)
        self._update_navigation()
        self.setStyleSheet(self._stylesheet())

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("setupSidebar")
        self.sidebar.setMinimumWidth(232)
        self.sidebar.setMaximumWidth(252)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(24, 24, 20, 22)
        sidebar_layout.setSpacing(9)
        self.brand_label = QLabel("HATIRLATICI")
        self.brand_label.setObjectName("setupBrand")
        self.brand_label.setWordWrap(True)
        self.wizard_label = QLabel()
        self.wizard_label.setObjectName("wizardLabel")
        self.wizard_label.setWordWrap(True)
        self.secure_label = QLabel()
        self.secure_label.setObjectName("secureLabel")
        self.secure_label.setWordWrap(True)
        sidebar_layout.addWidget(self.brand_label)
        sidebar_layout.addWidget(self.wizard_label)
        sidebar_layout.addWidget(self.secure_label)
        sidebar_layout.addSpacing(13)

        self.steps: list[tuple[QFrame, QLabel, QLabel, QLabel]] = []
        for index in range(5):
            frame = QFrame()
            frame.setObjectName("setupStep")
            frame.setProperty("state", "pending")
            row = QHBoxLayout(frame)
            row.setContentsMargins(8, 8, 7, 8)
            row.setSpacing(9)
            number = QLabel(str(index + 1))
            number.setObjectName("stepNumber")
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number.setFixedSize(28, 28)
            copy = QVBoxLayout()
            copy.setSpacing(1)
            title = QLabel()
            title.setObjectName("stepTitle")
            title.setWordWrap(True)
            subtitle = QLabel()
            subtitle.setObjectName("stepSubtitle")
            subtitle.setWordWrap(True)
            copy.addWidget(title)
            copy.addWidget(subtitle)
            row.addWidget(number, 0, Qt.AlignmentFlag.AlignTop)
            row.addLayout(copy, 1)
            sidebar_layout.addWidget(frame)
            self.steps.append((frame, number, title, subtitle))

        sidebar_layout.addStretch(1)
        self.privacy_footer = QLabel()
        self.privacy_footer.setObjectName("privacyFooter")
        self.privacy_footer.setWordWrap(True)
        sidebar_layout.addWidget(self.privacy_footer)
        root.addWidget(self.sidebar)

        main = QFrame()
        main.setObjectName("setupMain")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.pages = QStackedWidget()
        self.pages.setObjectName("setupPages")
        self.pages.addWidget(self._page_profile())
        self.pages.addWidget(self._page_delivery())
        self.pages.addWidget(self._page_email())
        self.pages.addWidget(self._page_gmail_guide())
        self.pages.addWidget(self._page_review())
        self.pages.currentChanged.connect(self._update_navigation)
        main_layout.addWidget(self.pages, 1)

        footer = QFrame()
        footer.setObjectName("setupFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(26, 12, 26, 14)
        footer_layout.setSpacing(10)
        self.exit_button = QPushButton()
        self.exit_button.setObjectName("subtleButton")
        self.exit_button.clicked.connect(self.reject)
        self.back_button = QPushButton()
        self.back_button.setObjectName("secondaryButton")
        self.back_button.clicked.connect(self._go_back)
        self.next_button = QPushButton()
        self.next_button.setObjectName("primaryButton")
        self.next_button.clicked.connect(self._go_next)
        self.next_button.setDefault(True)
        footer_layout.addWidget(self.exit_button)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.back_button)
        footer_layout.addWidget(self.next_button)
        main_layout.addWidget(footer)
        root.addWidget(main, 1)

    def _page_shell(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("pageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(34, 26, 34, 24)
        layout.setSpacing(14)
        scroll.setWidget(content)
        return scroll, layout

    @staticmethod
    def _copy_label(object_name: str, *, wrap: bool = True) -> QLabel:
        label = QLabel()
        label.setObjectName(object_name)
        label.setWordWrap(wrap)
        return label

    def _add_heading(self, layout: QVBoxLayout) -> tuple[QLabel, QLabel]:
        title = self._copy_label("pageTitle")
        subtitle = self._copy_label("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        return title, subtitle

    def _field_label(self) -> QLabel:
        label = self._copy_label("fieldLabel")
        label.setMinimumWidth(142)
        label.setMaximumWidth(180)
        label.setMinimumHeight(56)
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )
        return label

    def _page_profile(self) -> QWidget:
        page, layout = self._page_shell()
        self.profile_title, self.profile_subtitle = self._add_heading(layout)
        card = QFrame()
        card.setObjectName("contentCard")
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(13)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.name_label = self._field_label()
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("textInput")
        self.name_edit.setClearButtonEnabled(True)
        self.name_label.setBuddy(self.name_edit)
        self.language_label = self._field_label()
        self.language_selector = LanguageMenuButton()
        self.language_selector.languageChanged.connect(self._apply_language)
        self.language_label.setBuddy(self.language_selector)
        self.language_hint = self._copy_label("fieldHint")
        form.addRow(self.name_label, self.name_edit)
        form.addRow(self.language_label, self.language_selector)
        form.addRow(QWidget(), self.language_hint)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _page_delivery(self) -> QWidget:
        page, layout = self._page_shell()
        self.delivery_title, self.delivery_subtitle = self._add_heading(layout)
        cards = QHBoxLayout()
        cards.setSpacing(11)
        self.channel_cards = {
            "pc": ChoiceCard("pc", "monitor"),
            "email": ChoiceCard("email", "mail"),
            "both": ChoiceCard("both", "both"),
        }
        for card in self.channel_cards.values():
            card.chosen.connect(self._set_channel)
            cards.addWidget(card, 1)
        layout.addLayout(cards)
        self.delivery_info = self._copy_label("infoPanel")
        layout.addWidget(self.delivery_info)
        layout.addStretch(1)
        return page

    def _page_email(self) -> QWidget:
        page, layout = self._page_shell()
        self.email_title, self.email_subtitle = self._add_heading(layout)
        provider_row = QHBoxLayout()
        provider_row.setSpacing(11)
        self.provider_cards = {
            "gmail": ChoiceCard("gmail", "gmail"),
            "custom": ChoiceCard("custom", "server"),
        }
        for card in self.provider_cards.values():
            card.chosen.connect(self._set_provider)
            provider_row.addWidget(card, 1)
        layout.addLayout(provider_row)
        self.email_forms = QStackedWidget()
        self.email_forms.setObjectName("emailForms")

        gmail_card = QFrame()
        gmail_card.setObjectName("contentCard")
        gmail_form = QFormLayout(gmail_card)
        gmail_form.setContentsMargins(20, 18, 20, 18)
        gmail_form.setHorizontalSpacing(18)
        gmail_form.setVerticalSpacing(12)
        gmail_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.gmail_from_label = self._field_label()
        self.from_email = QLineEdit()
        self.from_email.setObjectName("textInput")
        self.gmail_from_label.setBuddy(self.from_email)
        self.gmail_to_label = self._field_label()
        self.to_email = QLineEdit()
        self.to_email.setObjectName("textInput")
        self.gmail_to_label.setBuddy(self.to_email)
        self.gmail_fixed_security = self._copy_label("infoPanel")
        gmail_form.addRow(self.gmail_from_label, self.from_email)
        gmail_form.addRow(self.gmail_to_label, self.to_email)
        gmail_form.addRow(QWidget(), self.gmail_fixed_security)

        custom_card = QFrame()
        custom_card.setObjectName("contentCard")
        custom_form = QFormLayout(custom_card)
        custom_form.setContentsMargins(20, 18, 20, 18)
        custom_form.setHorizontalSpacing(18)
        custom_form.setVerticalSpacing(11)
        custom_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.custom_from_label = self._field_label()
        self.custom_from_email = QLineEdit()
        self.custom_from_email.setObjectName("textInput")
        self.custom_from_label.setBuddy(self.custom_from_email)
        self.custom_to_label = self._field_label()
        self.custom_to_email = QLineEdit()
        self.custom_to_email.setObjectName("textInput")
        self.custom_to_label.setBuddy(self.custom_to_email)
        self.custom_user_label = self._field_label()
        self.custom_username = QLineEdit()
        self.custom_username.setObjectName("textInput")
        self.custom_user_label.setBuddy(self.custom_username)
        self.custom_host_label = self._field_label()
        self.custom_host = QLineEdit()
        self.custom_host.setObjectName("textInput")
        self.custom_host_label.setBuddy(self.custom_host)
        self.custom_port_label = self._field_label()
        self.custom_port = QSpinBox()
        self.custom_port.setObjectName("numberInput")
        self.custom_port.setRange(1, 65535)
        self.custom_port.setValue(587)
        self.custom_port_label.setBuddy(self.custom_port)
        self.custom_security_label = self._field_label()
        self.custom_security = QComboBox()
        self.custom_security.setObjectName("comboInput")
        # Populate semantic IDs before _load_existing selects a saved mode.
        self.custom_security.addItem(self._t("tls_starttls"), "starttls")
        self.custom_security.addItem(self._t("tls_implicit"), "implicit_tls")
        self.custom_security_label.setBuddy(self.custom_security)
        self.custom_secret_label = self._field_label()
        self.custom_secret_edit = QLineEdit()
        self.custom_secret_edit.setObjectName("textInput")
        self.custom_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.custom_secret_edit.setClearButtonEnabled(True)
        self.custom_secret_label.setBuddy(self.custom_secret_edit)
        custom_form.addRow(self.custom_from_label, self.custom_from_email)
        custom_form.addRow(self.custom_to_label, self.custom_to_email)
        custom_form.addRow(self.custom_user_label, self.custom_username)
        custom_form.addRow(self.custom_host_label, self.custom_host)
        custom_form.addRow(self.custom_port_label, self.custom_port)
        custom_form.addRow(self.custom_security_label, self.custom_security)
        custom_form.addRow(self.custom_secret_label, self.custom_secret_edit)
        self.email_forms.addWidget(gmail_card)
        self.email_forms.addWidget(custom_card)
        layout.addWidget(self.email_forms)
        layout.addStretch(1)
        return page

    def _guide_row(self) -> tuple[QFrame, QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("guideRow")
        row = QVBoxLayout(frame)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(3)
        title = self._copy_label("guideTitle")
        description = self._copy_label("guideDescription")
        row.addWidget(title)
        row.addWidget(description)
        return frame, title, description

    def _page_gmail_guide(self) -> QWidget:
        page, layout = self._page_shell()
        self.guide_title, self.guide_subtitle = self._add_heading(layout)
        self.never_password = self._copy_label("warningPanel")
        layout.addWidget(self.never_password)
        self.guide_rows: list[tuple[QFrame, QLabel, QLabel]] = []
        for _ in range(4):
            row = self._guide_row()
            self.guide_rows.append(row)
            layout.addWidget(row[0])
        links = QHBoxLayout()
        links.setSpacing(10)
        self.open_2sv_button = QPushButton()
        self.open_2sv_button.setObjectName("secondaryButton")
        self.open_2sv_button.clicked.connect(lambda: self._open_google_url(self.GOOGLE_2SV_URL))
        self.open_app_passwords_button = QPushButton()
        self.open_app_passwords_button.setObjectName("secondaryButton")
        self.open_app_passwords_button.clicked.connect(
            lambda: self._open_google_url(self.GOOGLE_APP_PASSWORDS_URL)
        )
        links.addWidget(self.open_2sv_button)
        links.addWidget(self.open_app_passwords_button)
        links.addStretch(1)
        layout.addLayout(links)
        self.missing_title = self._copy_label("guideTitle")
        self.missing_description = self._copy_label("guideDescription")
        layout.addWidget(self.missing_title)
        layout.addWidget(self.missing_description)
        secret_card = QFrame()
        secret_card.setObjectName("contentCard")
        secret_form = QFormLayout(secret_card)
        secret_form.setContentsMargins(20, 17, 20, 17)
        secret_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.gmail_secret_label = self._field_label()
        self.gmail_secret_edit = QLineEdit()
        self.gmail_secret_edit.setObjectName("textInput")
        self.gmail_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gmail_secret_edit.setClearButtonEnabled(True)
        self.gmail_secret_label.setBuddy(self.gmail_secret_edit)
        secret_form.addRow(self.gmail_secret_label, self.gmail_secret_edit)
        layout.addWidget(secret_card)
        layout.addStretch(1)
        return page

    def _review_row(self) -> tuple[QFrame, QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("reviewRow")
        row = QHBoxLayout(frame)
        row.setContentsMargins(15, 11, 15, 11)
        row.setSpacing(14)
        key = self._copy_label("reviewKey")
        key.setMinimumWidth(125)
        value = self._copy_label("reviewValue")
        row.addWidget(key)
        row.addWidget(value, 1)
        return frame, key, value

    def _page_review(self) -> QWidget:
        page, layout = self._page_shell()
        self.review_title, self.review_subtitle = self._add_heading(layout)
        self.review_rows = [self._review_row() for _ in range(5)]
        for frame, _key, _value in self.review_rows:
            layout.addWidget(frame)
        self.delete_credential = QCheckBox()
        self.delete_credential.setObjectName("deleteCredential")
        layout.addWidget(self.delete_credential)
        self.finish_note = self._copy_label("infoPanel")
        layout.addWidget(self.finish_note)
        layout.addStretch(1)
        return page

    def _load_existing(self) -> None:
        self.name_edit.setText(str(self._settings.get("profile_name", "")))
        self.from_email.setText(str(self._settings.get("mail_from_email", "")))
        self.to_email.setText(str(self._settings.get("mail_to_email", "")))
        self.custom_from_email.setText(str(self._settings.get("mail_from_email", "")))
        self.custom_to_email.setText(str(self._settings.get("mail_to_email", "")))
        self.custom_username.setText(str(self._settings.get("smtp_username", "")))
        self.custom_host.setText(str(self._settings.get("smtp_host", "")))
        try:
            port = int(self._settings.get("smtp_port", 587))
        except (TypeError, ValueError):
            port = 587
        self.custom_port.setValue(port if 1 <= port <= 65535 else 587)
        # Restore the saved protocol, not the first item in the selector.
        # Legacy profiles without a mode use the transport's port-465 default.
        security = str(self._settings.get("smtp_security", "")).strip().lower()
        if not security:
            security = "implicit_tls" if self.custom_port.value() == 465 else "starttls"
        self.custom_security.setCurrentIndex(self.custom_security.findData(security))

    def _t(self, key: str) -> str:
        return l10n.text(key, self.language)

    def _apply_language(self, language: str) -> None:
        self.language = l10n.normalize_language(language)
        if self.language_selector.current_language() != self.language:
            self.language_selector.select_language(self.language, emit=False)
        self.setWindowTitle(self._t("window_title"))
        self.brand_label.setText(self._t("brand"))
        self.wizard_label.setText(self._t("wizard_label"))
        self.secure_label.setText(self._t("secure_local"))
        self.privacy_footer.setText(self._t("privacy_footer"))
        step_keys = (
            ("step_profile", "step_profile_sub"),
            ("step_delivery", "step_delivery_sub"),
            ("step_email", "step_email_sub"),
            ("step_security", "step_security_sub"),
            ("step_ready", "step_ready_sub"),
        )
        for (_frame, _number, title, subtitle), (title_key, subtitle_key) in zip(self.steps, step_keys):
            title.setText(self._t(title_key))
            subtitle.setText(self._t(subtitle_key))

        self.profile_title.setText(self._t("welcome_title"))
        self.profile_subtitle.setText(self._t("welcome_sub"))
        self.name_label.setText(self._t("name"))
        self.name_edit.setPlaceholderText(self._t("name_placeholder"))
        self.language_label.setText(self._t("language"))
        self.language_selector.setAccessibleName(self._t("language"))
        self.language_hint.setText(self._t("language_hint"))
        self.delivery_title.setText(self._t("delivery_title"))
        self.delivery_subtitle.setText(self._t("delivery_sub"))
        self.channel_cards["pc"].set_copy(self._t("delivery_pc"), self._t("delivery_pc_desc"))
        self.channel_cards["email"].set_copy(self._t("delivery_email"), self._t("delivery_email_desc"))
        self.channel_cards["both"].set_copy(self._t("delivery_both"), self._t("delivery_both_desc"))
        self.delivery_info.setText(self._t("delivery_privacy_note"))

        self.email_title.setText(self._t("email_title"))
        self.email_subtitle.setText(self._t("email_sub"))
        self.provider_cards["gmail"].set_copy(self._t("gmail"), self._t("gmail_desc"))
        self.provider_cards["custom"].set_copy(self._t("custom"), self._t("custom_desc"))
        self.gmail_from_label.setText(self._t("from_email"))
        self.gmail_to_label.setText(self._t("to_email"))
        self.gmail_fixed_security.setText(self._t("gmail_fixed_security"))
        self.custom_from_label.setText(self._t("from_email_custom"))
        self.custom_to_label.setText(self._t("to_email"))
        self.custom_user_label.setText(self._t("smtp_username"))
        self.custom_host_label.setText(self._t("smtp_host"))
        self.custom_port_label.setText(self._t("smtp_port"))
        self.custom_security_label.setText(self._t("smtp_security"))
        self.custom_secret_label.setText(self._t("smtp_secret"))
        self.custom_host.setPlaceholderText(self._t("smtp_host_placeholder"))
        self.custom_secret_edit.setPlaceholderText(self._credential_placeholder("smtp_secret_placeholder"))
        current_security = self.custom_security.currentData()
        self.custom_security.blockSignals(True)
        self.custom_security.clear()
        self.custom_security.addItem(self._t("tls_starttls"), "starttls")
        self.custom_security.addItem(self._t("tls_implicit"), "implicit_tls")
        index = self.custom_security.findData(current_security)
        self.custom_security.setCurrentIndex(index)
        self.custom_security.blockSignals(False)

        self.guide_title.setText(self._t("gmail_guide_title"))
        self.guide_subtitle.setText(self._t("gmail_guide_sub"))
        self.never_password.setText(self._t("never_google_password"))
        for index, (_frame, title, description) in enumerate(self.guide_rows, start=1):
            title.setText(self._t(f"guide_step_{index}"))
            description.setText(self._t(f"guide_step_{index}_desc"))
        self.open_2sv_button.setText(self._t("open_2sv"))
        self.open_app_passwords_button.setText(self._t("open_app_passwords"))
        self.missing_title.setText(self._t("why_missing"))
        self.missing_description.setText(self._t("why_missing_desc"))
        self.gmail_secret_label.setText(self._t("app_password"))
        self.gmail_secret_edit.setPlaceholderText(self._credential_placeholder("app_password_placeholder"))

        self.review_title.setText(self._t("review_title"))
        self.review_subtitle.setText(self._t("review_sub"))
        for (_frame, key, _value), key_name in zip(
            self.review_rows,
            ("review_profile", "review_language", "review_delivery", "review_email", "review_security"),
        ):
            key.setText(self._t(key_name))
        self.delete_credential.setText(self._t("delete_stored_credential"))
        self.finish_note.setText(self._t("finish_note"))
        self.exit_button.setText(self._t("exit"))
        self.back_button.setText(self._t("back"))
        self._refresh_review()
        self._update_navigation()

    def _credential_placeholder(self, default_key: str) -> str:
        if credential_vault.has_smtp_credential():
            return self._t("stored_credential_placeholder")
        return self._t(default_key)

    def _set_channel(self, channel: str) -> None:
        if channel not in setup_model.CHANNELS:
            return
        self.selected_channel = channel
        for value, card in self.channel_cards.items():
            card.set_selected(value == channel)
        self._refresh_review()
        self._update_navigation()

    def _set_provider(self, provider: str) -> None:
        if provider not in setup_model.PROVIDERS:
            return
        self.selected_provider = provider
        for value, card in self.provider_cards.items():
            card.set_selected(value == provider)
        self.email_forms.setCurrentIndex(0 if provider == "gmail" else 1)
        self._refresh_review()
        self._update_navigation()

    def collect_payload(self) -> dict[str, object]:
        custom = self.selected_provider == "custom"
        return setup_model.normalize_setup(
            {
                "profile_name": self.name_edit.text(),
                "language": self.language,
                "default_channel": self.selected_channel,
                "email_enabled": self.selected_channel in {"email", "both"},
                "smtp_provider": self.selected_provider,
                "mail_from_email": self.custom_from_email.text() if custom else self.from_email.text(),
                "mail_to_email": self.custom_to_email.text() if custom else self.to_email.text(),
                "smtp_username": self.custom_username.text() if custom else self.from_email.text(),
                "smtp_host": self.custom_host.text() if custom else "smtp.gmail.com",
                "smtp_port": self.custom_port.value() if custom else 587,
                "smtp_security": self.custom_security.currentData() if custom else "starttls",
            }
        )

    def _entered_secret(self) -> str:
        return self.custom_secret_edit.text() if self.selected_provider == "custom" else self.gmail_secret_edit.text()

    def _validate_current_page(self) -> list[str]:
        page = self.pages.currentIndex()
        if page == 0:
            return setup_model.validate_profile(self.collect_payload(), language=self.language)
        if page == 2:
            return setup_model.validate_email(self.collect_payload(), language=self.language)
        if page == 3 and not self._entered_secret() and not credential_vault.has_smtp_credential():
            return [self._t("app_password_required")]
        return []

    def _show_notice(self, title: str, messages: list[str] | str) -> None:
        body = messages if isinstance(messages, str) else "\n".join(f"• {message}" for message in messages)
        notice = NoticeDialog(self, title, body, self._t("ok"))
        notice.setStyleSheet(self.styleSheet())
        notice.exec()

    def _go_next(self) -> None:
        errors = self._validate_current_page()
        if errors:
            self._show_notice(self._t("required_title"), errors)
            return
        page = self.pages.currentIndex()
        if page == 0:
            target = 1
        elif page == 1:
            target = 4 if self.selected_channel == "pc" else 2
        elif page == 2:
            target = 4 if self.selected_provider == "custom" else 3
        elif page == 3:
            target = 4
        else:
            self._save()
            return
        self.pages.setCurrentIndex(target)

    def _go_back(self) -> None:
        page = self.pages.currentIndex()
        if page == 4:
            target = 1 if self.selected_channel == "pc" else (2 if self.selected_provider == "custom" else 3)
        elif page == 3:
            target = 2
        elif page == 2:
            target = 1
        else:
            target = max(0, page - 1)
        self.pages.setCurrentIndex(target)

    def _skipped_steps(self) -> set[int]:
        if self.selected_channel == "pc":
            return {2, 3}
        if self.selected_provider == "custom":
            return {3}
        return set()

    def _update_navigation(self, *_args: object) -> None:
        if not hasattr(self, "pages"):
            return
        page = self.pages.currentIndex()
        skipped = self._skipped_steps()
        subtitle_keys = (
            "step_profile_sub",
            "step_delivery_sub",
            "step_email_sub",
            "step_security_sub",
            "step_ready_sub",
        )
        for index, (frame, number, _title, subtitle) in enumerate(self.steps):
            if index in skipped:
                state = "skipped"
                number.setText("–")
                subtitle.setText(self._t("skipped"))
            else:
                subtitle.setText(self._t(subtitle_keys[index]))
                if index == page:
                    state = "current"
                    number.setText(str(index + 1))
                elif index < page:
                    state = "complete"
                    number.setText("✓")
                else:
                    state = "pending"
                    number.setText(str(index + 1))
            frame.setProperty("state", state)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
        self.back_button.setVisible(page > 0)
        self.next_button.setText(self._t("finish") if page == 4 else self._t("next"))
        self._refresh_review()

    def _refresh_review(self) -> None:
        if not hasattr(self, "review_rows"):
            return
        skipped = self._t("skipped")
        values = [
            self.name_edit.text().strip() or "—",
            l10n.LANGUAGE_NAMES[self.language],
            self._t({"pc": "delivery_pc", "email": "delivery_email", "both": "delivery_both"}[self.selected_channel]),
            skipped if self.selected_channel == "pc" else self._t(self.selected_provider),
            skipped if self.selected_channel == "pc" else self._t("security_value"),
        ]
        for (_frame, _key, value_label), value in zip(self.review_rows, values):
            value_label.setText(value)
        self.delete_credential.setVisible(self.selected_channel == "pc" and credential_vault.has_smtp_credential())

    def _open_google_url(self, url: str) -> None:
        if not QDesktopServices.openUrl(QUrl(url)):
            self._show_notice(self._t("required_title"), self._t("open_failed"))

    def _save(self) -> None:
        if self.preview:
            self._show_notice(self._t("preview_mode"), self._t("preview_save_blocked"))
            return
        if getattr(self, "_save_in_progress", False):
            return
        payload = self.collect_payload()
        errors = setup_model.validate_setup(payload, language=self.language)
        email_enabled = bool(payload.get("email_enabled", False))
        entered_secret = self._entered_secret()
        existing_secret = credential_vault.has_smtp_credential()
        if email_enabled and not entered_secret and not existing_secret:
            errors.append(self._t("custom_required") if self.selected_provider == "custom" else self._t("app_password_required"))
        if errors:
            self._show_notice(self._t("required_title"), errors)
            return

        failure_key = ""
        self._save_in_progress = True
        self.next_button.setEnabled(False)
        try:
            # Settings failure must not leave a newly replaced/deleted vault.
            with setup_persistence.protect_setup_files():
                if email_enabled and entered_secret:
                    credential_vault.store_smtp_credential(entered_secret)
                    existing_secret = True
                if not email_enabled and self.delete_credential.isChecked():
                    credential_vault.delete_smtp_credential()
                    existing_secret = False
                payload["email_ready"] = bool(email_enabled and existing_secret)
                payload["mail_transport_v2_ready"] = bool(email_enabled and existing_secret)
                merged = dict(self._settings)
                merged.update(payload)
                runtime_config.save_settings(merged)
        except setup_persistence.SetupRollbackError:
            failure_key = "setup_restore_failed"
        except credential_vault.CredentialVaultError:
            failure_key = "credential_save_failed"
        except (OSError, ValueError, TypeError):
            # Never pass exception strings or account details into the dialog.
            failure_key = "setup_save_failed"
        finally:
            self._save_in_progress = False
            self.next_button.setEnabled(True)
            self.gmail_secret_edit.clear()
            self.custom_secret_edit.clear()

        if failure_key:
            self._show_notice(self._t("required_title"), self._t(failure_key))
            return
        self._settings = merged
        self.accept()

    @staticmethod
    def _stylesheet() -> str:
        return r"""
QDialog#guidedFirstRun, QDialog#noticeDialog { background: #071018; color: #F2F7FA; }
QFrame#setupSidebar { background: #09131C; border-right: 1px solid #20313D; }
QFrame#setupMain, QWidget#pageContent, QStackedWidget#setupPages, QScrollArea#pageScroll { background: #0A121A; border: none; }
QLabel { color: #DDE7EC; font-size: 13px; }
QLabel#setupBrand { color: #43D6DC; font-size: 13px; font-weight: 800; letter-spacing: 2px; }
QLabel#wizardLabel { color: #F4F8FA; font-size: 19px; font-weight: 800; }
QLabel#secureLabel { color: #74A7AA; font-size: 10px; font-weight: 700; }
QLabel#privacyFooter { color: #72838F; font-size: 10px; }
QFrame#setupStep { background: transparent; border: 1px solid transparent; border-radius: 10px; }
QFrame#setupStep[state="current"] { background: #10232C; border-color: #245A62; }
QFrame#setupStep[state="complete"] { background: #0C191F; }
QFrame#setupStep[state="skipped"] { background: #0A1117; }
QLabel#stepNumber { color: #91A3AE; background: #111E27; border: 1px solid #2B414E; border-radius: 14px; font-weight: 700; }
QFrame#setupStep[state="current"] QLabel#stepNumber { color: #071014; background: #43D6DC; border-color: #43D6DC; }
QFrame#setupStep[state="complete"] QLabel#stepNumber { color: #65D6A2; border-color: #276D51; }
QFrame#setupStep[state="skipped"] QLabel { color: #5E6D77; }
QLabel#stepTitle { color: #E8EFF2; font-size: 12px; font-weight: 700; }
QLabel#stepSubtitle { color: #80909C; font-size: 10px; }
QLabel#pageTitle { color: #F5F9FA; font-size: 25px; font-weight: 800; }
QLabel#pageSubtitle { color: #91A2AE; font-size: 13px; }
QFrame#contentCard, QFrame#reviewRow, QFrame#guideRow { background: #0E1922; border: 1px solid #263B48; border-radius: 12px; }
QLabel#fieldLabel, QLabel#reviewKey, QLabel#guideTitle { color: #DDE8EC; font-weight: 700; }
QLabel#fieldHint, QLabel#guideDescription { color: #899AA6; }
QLabel#reviewValue { color: #F2F7F8; }
QLabel#infoPanel, QLabel#warningPanel { color: #A9BAC3; background: #0D1D25; border: 1px solid #24505A; border-radius: 9px; padding: 10px 12px; }
QLabel#warningPanel { color: #F1C786; border-color: #70572E; background: #19170F; font-weight: 700; }
QLineEdit#textInput, QSpinBox#numberInput, QComboBox#comboInput, QToolButton#languageSelector { min-height: 42px; color: #F3F7F9; background: #09131B; border: 1px solid #304553; border-radius: 9px; padding: 0 12px; selection-background-color: #1B858D; }
QLineEdit#textInput:focus, QSpinBox#numberInput:focus, QComboBox#comboInput:focus, QToolButton#languageSelector:focus { border: 2px solid #43D6DC; }
QToolButton#languageSelector { text-align: left; padding-right: 34px; }
QToolButton#languageSelector::menu-indicator { subcontrol-position: right center; right: 12px; }
QMenu#languageMenu { background: #101B24; color: #F2F7F9; border: 1px solid #314854; padding: 6px; }
QMenu#languageMenu::item { min-width: 210px; min-height: 30px; padding: 6px 12px; border-radius: 6px; }
QMenu#languageMenu::item:selected { background: #12323A; color: #52DEE2; }
QFrame#choiceCard { background: #0D1821; border: 1px solid #2A3E4B; border-radius: 12px; }
QFrame#choiceCard:hover { background: #11212B; border-color: #3B6670; }
QFrame#choiceCard:focus { border: 2px solid #67E1E4; }
QFrame#choiceCard[selected="true"] { background: #10252D; border: 2px solid #39CED4; }
QLabel#choiceTitle { color: #EEF5F6; font-size: 14px; font-weight: 750; }
QLabel#choiceDescription { color: #8FA1AC; font-size: 11px; }
QFrame#setupFooter { background: #09131B; border-top: 1px solid #20313D; }
QPushButton { min-height: 40px; border-radius: 9px; padding: 0 18px; font-weight: 700; }
QPushButton#primaryButton { color: #061015; background: #43D6DC; border: 1px solid #43D6DC; }
QPushButton#primaryButton:hover { background: #60E4E7; }
QPushButton#primaryButton:focus { border: 2px solid #FFFFFF; }
QPushButton#secondaryButton { color: #DDE8EC; background: #111E27; border: 1px solid #354A57; }
QPushButton#secondaryButton:hover { background: #172A35; border-color: #4B7380; }
QPushButton#secondaryButton:focus, QPushButton#subtleButton:focus { border: 2px solid #67E1E4; }
QPushButton#subtleButton { color: #8FA0AB; background: transparent; border: 1px solid transparent; }
QPushButton#subtleButton:hover { color: #DDE8EC; background: #111B23; }
QCheckBox#deleteCredential { color: #D7E1E5; spacing: 9px; }
QLabel#noticeTitle { color: #F5F8FA; font-size: 20px; font-weight: 800; }
QLabel#noticeBody { color: #B8C6CD; font-size: 13px; }
QScrollBar:vertical { background: #0A121A; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #304753; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def run_setup(*, force: bool = False, preview: bool = False) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    QApplication.setApplicationName("Hatırlatıcı")
    dialog = GuidedFirstRunDialog(force=force, preview=preview)
    return int(dialog.exec())


def main() -> int:
    force = "--force" in sys.argv
    preview = "--preview" in sys.argv
    preview_root: tempfile.TemporaryDirectory[str] | None = None
    if preview:
        preview_root = tempfile.TemporaryDirectory(prefix="hatirlatici-preview-")
        base = Path(preview_root.name)
        os.environ["XDG_CONFIG_HOME"] = str(base / "config")
        os.environ["XDG_DATA_HOME"] = str(base / "data")
        os.environ["XDG_STATE_HOME"] = str(base / "state")
    try:
        result = run_setup(force=force, preview=preview)
    finally:
        if preview_root is not None:
            preview_root.cleanup()
    return 0 if result == QDialog.DialogCode.Accepted else 10


if __name__ == "__main__":
    raise SystemExit(main())
