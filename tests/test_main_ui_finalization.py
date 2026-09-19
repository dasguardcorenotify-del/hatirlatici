import ast
import datetime as dt
import fcntl
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "ui_v2"

for path in (str(ROOT), str(UI_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
)
from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtNetwork import QLocalServer

import l10n
import runtime_config
import app_identity
import core_v2 as core
import hatirlatici_app
import premium_preview as base
import hatirlatici_ultimate
from language_menu import LanguageMenuButton
from hatirlatici_ultimate import FinalPolishWindow


class MainUiFinalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.previous = {
            name: os.environ.get(name)
            for name in (
                "XDG_CONFIG_HOME",
                "XDG_DATA_HOME",
                "XDG_STATE_HOME",
            )
        }
        os.environ["XDG_CONFIG_HOME"] = str(root / "config")
        os.environ["XDG_DATA_HOME"] = str(root / "data")
        os.environ["XDG_STATE_HOME"] = str(root / "state")
        self.runtime_root = root
        self.bound_paths = {}

        def bind(module, name, value):
            self.bound_paths[(module, name)] = getattr(module, name)
            setattr(module, name, value)

        data = root / "data" / "hatirlatici"
        state = root / "state" / "hatirlatici"
        config = root / "config" / "hatirlatici"
        bind(base, "CSV_PATH", data / "hatirlatmalar.csv")
        bind(base, "LOCK_PATH", state / "locks" / "hatirlatmalar.lock")
        bind(base, "BACKUP_PATH", state / "data_backups")
        bind(core, "ROOT", data)
        bind(core, "MAIL_CSV", data / "hatirlatmalar.csv")
        bind(core, "PC_CSV", data / "pc_hatirlatmalar.csv")
        bind(core, "HISTORY_CSV", state / "hatirlatici_history.csv")
        bind(core, "MAIL_LOCK", state / "locks" / "hatirlatmalar.lock")
        bind(core, "PC_LOCK", state / "locks" / "pc_hatirlatmalar.lock")
        bind(core, "HISTORY_LOCK", state / "locks" / "hatirlatici_history.lock")
        bind(core, "SETTINGS_JSON", config / "settings_v2.json")
        bind(core, "DATA_BACKUPS", state / "data_backups")

    def tearDown(self):
        for (module, name), value in self.bound_paths.items():
            setattr(module, name, value)
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp.cleanup()

    @staticmethod
    def visible_text(window):
        values = []
        for widget_type in (
            QLabel,
            QPushButton,
            QCheckBox,
            QToolButton,
        ):
            values.extend(
                widget.text()
                for widget in window.findChildren(widget_type)
                if widget.text()
            )
        for widget in window.findChildren(QLineEdit):
            if widget.placeholderText():
                values.append(widget.placeholderText())
        for widget in window.findChildren(QTextEdit):
            if widget.placeholderText():
                values.append(widget.placeholderText())
        for widget in window.findChildren(QComboBox):
            values.extend(
                widget.itemText(index)
                for index in range(widget.count())
            )
        return "\n".join(values)

    def test_main_pages_are_localized_from_semantic_ids(self):
        for path in (
            base.CSV_PATH,
            base.LOCK_PATH,
            base.BACKUP_PATH,
            core.MAIL_CSV,
            core.PC_CSV,
            core.HISTORY_CSV,
            core.SETTINGS_JSON,
        ):
            self.assertTrue(
                Path(path).resolve().is_relative_to(
                    self.runtime_root.resolve()
                ),
                path,
            )

        forbidden_turkish = (
            "Bugün",
            "Hatırlatmalar",
            "Geçmiş",
            "Ayarlar",
            "Yeni Hatırlatma",
            "Ne hatırlatayım",
            "Tarih",
            "Saat",
            "Tekrar",
            "Kategori",
            "Kullanıcı",
            "Duraklat",
            "Etkinleştir",
            "Kaydet",
            "CANLI VERİ",
            "Premium Hatırlatıcı",
        )

        with (
            mock.patch.object(core, "load_groups", return_value=[]),
            mock.patch.object(core, "load_history", return_value=[]),
            mock.patch.object(core, "load_settings", return_value={}),
            mock.patch.object(hatirlatici_app, "service_active", return_value=True),
            mock.patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
        ):
            for language in ("de", "es", "ru"):
                with self.subTest(language=language):
                    runtime_config.save_settings(
                        {
                            "setup_complete": True,
                            "profile_name": "Ada",
                            "language": language,
                            "default_channel": "pc",
                        }
                    )
                    window = FinalPolishWindow()
                    window.resize(960, 680)
                    window.show()
                    self.app.processEvents()

                    self.assertEqual(window.language, language)
                    self.assertEqual(window.profile_name, "Ada")
                    self.assertEqual(window.default_channel, "pc")
                    self.assertEqual(window.current_page, "today")
                    self.assertEqual(
                        [button.page_id for button in window.nav_buttons],
                        ["today", "reminders", "history", "settings"],
                    )

                    page_text = [self.visible_text(window)]
                    for page_id in ("reminders", "history", "settings"):
                        window.switch_page(page_id)
                        self.app.processEvents()
                        self.assertEqual(window.current_page, page_id)
                        page_text.append(self.visible_text(window))

                    combined = "\n".join(page_text)
                    visible_lines = {
                        line.strip()
                        for line in combined.splitlines()
                    }
                    for phrase in forbidden_turkish:
                        self.assertNotIn(
                            phrase,
                            visible_lines,
                            (language, phrase, combined),
                        )

                    self.assertIn(l10n.text("nav_today", language), combined)
                    self.assertIn(l10n.text("nav_settings", language), combined)
                    self.assertIn(l10n.text("system_status", language), combined)
                    self.assertIn(l10n.text("today_no_active", language), combined)
                    self.assertIn(l10n.text("no_filter_match", language), combined)
                    self.assertIn(l10n.text("history_empty", language), combined)
                    self.assertNotIn("Kullanıcı Kullanıcı", combined)
                    self.assertEqual(
                        tuple(
                            button.text()
                            for button in window.support_link_buttons
                        ),
                        tuple(
                            l10n.text(key, language)
                            for key, _url in hatirlatici_ultimate.SUPPORT_LINKS
                        ),
                    )
                    self.assertEqual(
                        tuple(
                            button.property("external_url")
                            for button in window.support_link_buttons
                        ),
                        tuple(
                            url
                            for _key, url in hatirlatici_ultimate.SUPPORT_LINKS
                        ),
                    )
                    with mock.patch.object(
                        hatirlatici_ultimate.QDesktopServices,
                        "openUrl",
                        return_value=False,
                    ) as open_url:
                        window.support_link_buttons[0].click()
                        self.app.processEvents()
                    opened = open_url.call_args.args[0]
                    self.assertEqual(
                        opened.toString(),
                        app_identity.SOURCE_REPOSITORY_URL,
                    )
                    self.assertEqual(
                        window.preview_status.text(),
                        l10n.text("external_link_failed", language),
                    )
                    window.close()
                    window.deleteLater()
                    self.app.processEvents()

    def test_settings_language_menu_is_shared_accessible_and_live(self):
        original_settings = {
            "setup_complete": True,
            "profile_name": "Ada",
            "language": "en",
            "default_channel": "pc",
            "future_setting": {"preserve": True},
        }
        runtime_config.save_settings(original_settings)

        with (
            mock.patch.object(core, "load_groups", return_value=[]),
            mock.patch.object(core, "load_history", return_value=[]),
            mock.patch.object(core, "load_settings", return_value={}),
            mock.patch.object(hatirlatici_app, "service_active", return_value=True),
            mock.patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
        ):
            window = FinalPolishWindow()
            window.resize(960, 680)
            window.show()
            window.switch_page("settings")
            self.app.processEvents()

            button = window.language_button
            self.assertIsInstance(button, LanguageMenuButton)
            self.assertEqual(
                button.popupMode(),
                QToolButton.ToolButtonPopupMode.InstantPopup,
            )
            self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.StrongFocus)
            button.setFocus(Qt.FocusReason.OtherFocusReason)
            self.app.processEvents()
            self.assertTrue(button.hasFocus())
            self.assertEqual(button.current_language(), "en")
            self.assertEqual(button.text(), l10n.LANGUAGE_NAMES["en"])
            self.assertFalse(
                any(glyph in button.text() for glyph in ("▾", "▼", "⌄"))
            )

            actions = button.menu().actions()
            self.assertEqual(
                [action.data() for action in actions],
                list(l10n.SUPPORTED_LANGUAGES),
            )
            self.assertEqual(
                [action.text() for action in actions],
                [
                    l10n.LANGUAGE_NAMES[code]
                    for code in l10n.SUPPORTED_LANGUAGES
                ],
            )
            self.assertEqual(
                [action.data() for action in actions if action.isChecked()],
                ["en"],
            )

            window.tray = QSystemTrayIcon(window)
            window._rebuild_final_tray()
            next(
                action for action in actions if action.data() == "de"
            ).trigger()
            self.app.processEvents()

            saved = runtime_config.load_settings()
            self.assertEqual(saved["language"], "de")
            self.assertEqual(saved["future_setting"], {"preserve": True})
            self.assertEqual(window.language, "de")
            self.assertEqual(window.current_page, "settings")
            self.assertEqual(window.windowTitle(), l10n.text("app_name", "de"))
            self.assertEqual(
                [nav.text() for nav in window.nav_buttons],
                [
                    l10n.text(key, "de")
                    for key in (
                        "nav_today",
                        "nav_reminders",
                        "nav_history",
                        "nav_settings",
                    )
                ],
            )
            visible_selectors = [
                selector
                for selector in window.findChildren(LanguageMenuButton)
                if selector.isVisibleTo(window)
            ]
            self.assertEqual(len(visible_selectors), 1)
            self.assertEqual(visible_selectors[0].current_language(), "de")
            self.assertEqual(
                window.preview_status.text(),
                l10n.text("language_changed", "de"),
            )

            tray_labels = {
                action.text()
                for action in window._final_tray_menu.actions()
                if not action.isSeparator()
            }
            for key in (
                "tray_open",
                "tray_quick",
                "nav_today",
                "nav_reminders",
                "nav_history",
                "nav_settings",
                "quit",
            ):
                translated = l10n.text(key, "de")
                self.assertTrue(
                    any(translated in label for label in tray_labels),
                    (key, tray_labels),
                )

            for page_id, key in (
                ("today", "nav_today"),
                ("reminders", "nav_reminders"),
                ("history", "nav_history"),
                ("settings", "nav_settings"),
            ):
                window.switch_page(page_id)
                self.app.processEvents()
                self.assertIn(l10n.text(key, "de"), self.visible_text(window))
                if page_id != "settings":
                    self.assertIsNone(window.language_button)

            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_live_language_switch_survives_deferred_page_deletion(self):
        with (
            mock.patch.object(core, "load_groups", return_value=[]),
            mock.patch.object(core, "load_history", return_value=[]),
            mock.patch.object(core, "load_settings", return_value={}),
            mock.patch.object(hatirlatici_app, "service_active", return_value=True),
            mock.patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
        ):
            for page_id in ("today", "reminders", "history", "settings"):
                runtime_config.save_settings(
                    {
                        "setup_complete": True,
                        "profile_name": "Ada",
                        "language": "en",
                        "default_channel": "pc",
                    }
                )
                window = FinalPolishWindow()
                window.resize(960, 680)
                window.show()
                window.switch_page(page_id)
                self.app.processEvents()
                QCoreApplication.sendPostedEvents(
                    None,
                    QEvent.Type.DeferredDelete,
                )
                if page_id != "settings":
                    self.assertIsNone(window.language_button)

                for language in l10n.SUPPORTED_LANGUAGES:
                    with self.subTest(page=page_id, language=language):
                        window._change_language(language)
                        self.app.processEvents()
                        QCoreApplication.sendPostedEvents(
                            None,
                            QEvent.Type.DeferredDelete,
                        )
                        self.app.processEvents()
                        self.assertEqual(window.language, language)
                        self.assertEqual(window.current_page, page_id)
                        self.assertEqual(
                            window.windowTitle(),
                            l10n.text("app_name", language),
                        )
                        self.assertEqual(
                            [button.text() for button in window.nav_buttons],
                            [
                                l10n.text(key, language)
                                for key in (
                                    "nav_today",
                                    "nav_reminders",
                                    "nav_history",
                                    "nav_settings",
                                )
                            ],
                        )

                window.close()
                window.deleteLater()
                QCoreApplication.sendPostedEvents(
                    None,
                    QEvent.Type.DeferredDelete,
                )
                self.app.processEvents()

    def test_localized_choices_preserve_semantic_values(self):
        language = "es"
        self.assertEqual(base.channel_label("both", language), "Ambos")
        self.assertEqual(base.localized_repeat("weekly", language), "Cada semana")
        self.assertEqual(base.localized_category("Sağlık", language), "Salud")
        self.assertEqual(
            l10n.text("notification_snooze_minutes", "de", minutes=15),
            "15 Min. später",
        )
        self.assertEqual(
            base.localized_today_count(1, "en"),
            "You have 1 reminder today",
        )
        self.assertEqual(
            base.localized_today_count(2, "en"),
            "You have 2 reminders today",
        )
        self.assertEqual(
            base.localized_today_count(1, "de"),
            "Du hast heute 1 Erinnerung",
        )
        self.assertEqual(
            base.localized_today_count(2, "de"),
            "Du hast heute 2 Erinnerungen",
        )
        self.assertEqual(
            base.localized_today_count(1, "es"),
            "Tienes 1 recordatorio hoy",
        )
        self.assertEqual(
            base.localized_today_count(2, "ru"),
            "На сегодня у вас 2 напоминания",
        )
        self.assertEqual(
            base.localized_today_count(5, "ru"),
            "На сегодня у вас 5 напоминаний",
        )
        self.assertEqual(
            base.localized_today_count(21, "ru"),
            "На сегодня у вас 21 напоминание",
        )
        moment = dt.datetime(2026, 8, 20, 9, 5)
        self.assertEqual(
            base.format_datetime(moment, "en"),
            "8/20/26 • 09:05",
        )
        self.assertEqual(
            base.format_datetime(moment, "de"),
            "20.08.26 • 09:05",
        )
        self.assertEqual(
            base.format_datetime(moment, "es"),
            "20/8/26 • 09:05",
        )
        self.assertEqual(
            base.format_datetime(moment, "ru"),
            "20.08.2026 • 09:05",
        )

    def test_support_links_and_safe_scheduler_status_are_canonical(self):
        self.assertEqual(
            FinalPolishWindow.VERSION,
            app_identity.APP_VERSION,
        )
        expected_links = (
            (
                "source_repository",
                "https://github.com/dasguardcorenotify-del/hatirlatici",
            ),
            (
                "privacy_policy",
                "https://github.com/dasguardcorenotify-del/hatirlatici/blob/v2.0.0/PRIVACY.md",
            ),
            (
                "report_issue",
                "https://github.com/dasguardcorenotify-del/hatirlatici/issues",
            ),
            (
                "support_help",
                "https://github.com/dasguardcorenotify-del/hatirlatici/blob/v2.0.0/SUPPORT.md",
            ),
        )
        self.assertEqual(hatirlatici_ultimate.SUPPORT_LINKS, expected_links)
        expected_labels = {
            "tr": ("Kaynak kodu", "Gizlilik", "Sorun bildir", "Yardım ve destek"),
            "en": ("Source repository", "Privacy", "Report an issue", "Help and support"),
            "de": ("Quellcode", "Datenschutz", "Problem melden", "Hilfe und Support"),
            "es": ("Código fuente", "Privacidad", "Informar de un problema", "Ayuda y soporte"),
            "ru": ("Исходный код", "Конфиденциальность", "Сообщить о проблеме", "Помощь и поддержка"),
        }
        keys = tuple(key for key, _url in expected_links)
        for language, labels in expected_labels.items():
            with self.subTest(language=language):
                self.assertEqual(
                    tuple(l10n.text(key, language) for key in keys),
                    labels,
                )

        for status in (
            "pc-error:worker",
            "pc-error:interrupted",
            "pc-error:generic",
            "pc-error:process",
            "pc-script-missing",
        ):
            self.assertEqual(
                hatirlatici_ultimate.pc_delivery_status_key(status),
                "notification_delivery_failed",
            )
        for status in ("pc-ok", "running", "stopped"):
            self.assertIsNone(
                hatirlatici_ultimate.pc_delivery_status_key(status)
            )

    def test_malformed_quick_time_is_a_safe_localized_failure(self):
        runtime_config.save_settings(
            {
                "profile_name": "Ada",
                "language": "en",
                "default_channel": "pc",
            }
        )
        with (
            mock.patch.object(core, "load_groups", return_value=[]),
            mock.patch.object(core, "load_history", return_value=[]),
            mock.patch.object(core, "load_settings", return_value={}),
            mock.patch.object(hatirlatici_app, "service_active", return_value=True),
            mock.patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False),
        ):
            window = FinalPolishWindow()
            window.quick_input.setText("call Alex tomorrow at 24")
            with mock.patch.object(
                hatirlatici_ultimate,
                "parse_quick",
                side_effect=ValueError("raw parser detail"),
            ):
                window.quick_to_form()
                self.assertEqual(
                    window.preview_status.text(),
                    l10n.text("quick_parse_failed", "en"),
                )
                window.quick_save()
                self.assertEqual(
                    window.preview_status.text(),
                    l10n.text("quick_parse_failed", "en"),
                )
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_no_literal_user_facing_pyqt_localization_debt(self):
        """Fail when a visible Qt surface bypasses the localization API."""
        files = tuple(
            sorted(
                (*ROOT.glob("*.py"), *UI_ROOT.glob("*.py")),
                key=lambda path: str(path.relative_to(ROOT)),
            )
        )
        first_argument_calls = {
            "QLabel",
            "QPushButton",
            "QCheckBox",
            "QGroupBox",
            "QMenu",
            "QMessageBox",
            "setText",
            "setPlaceholderText",
            "setToolTip",
            "setAccessibleName",
            "setAccessibleDescription",
            "setWindowTitle",
            "setApplicationDisplayName",
            "setTitle",
            "setInformativeText",
            "addItem",
            "show_status",
        }
        all_argument_calls = {
            "QAction",
            "addAction",
            "_page_shell",
            "_setting_card",
        }
        dialog_calls = {
            "critical",
            "information",
            "question",
            "warning",
        }
        debt = []
        allowed_brand_literals = {
            # Registered product wordmark; localized at runtime elsewhere.
            "HATIRLATICI",
        }

        def literal_text(node):
            try:
                value = ast.literal_eval(node)
            except (ValueError, TypeError):
                return None
            if isinstance(value, str) and any(char.isalpha() for char in value):
                return value
            return None

        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                name = (
                    function.id
                    if isinstance(function, ast.Name)
                    else function.attr
                    if isinstance(function, ast.Attribute)
                    else ""
                )
                indexes = []
                if name in first_argument_calls:
                    indexes = [0]
                elif name in all_argument_calls:
                    indexes = list(range(len(node.args)))
                elif name in dialog_calls:
                    indexes = [1, 2]
                elif name == "showMessage":
                    indexes = [0, 1]
                elif name in {"add_notification", "notify_and_wait"}:
                    indexes = [1, 2]
                elif name == "set_content":
                    indexes = [0]

                for index in indexes:
                    if index >= len(node.args):
                        continue
                    value = literal_text(node.args[index])
                    if (
                        value is not None
                        and value not in allowed_brand_literals
                    ):
                        debt.append(f"{path.relative_to(ROOT)}:{node.lineno}:{name}:{value}")

                if name in {"save_group", "send_reminder"}:
                    for keyword in node.keywords:
                        if keyword.arg not in {"title", "subject", "body"}:
                            continue
                        value = literal_text(keyword.value)
                        if value is not None:
                            debt.append(
                                f"{path.relative_to(ROOT)}:{node.lineno}:"
                                f"{name}.{keyword.arg}:{value}"
                            )

        self.assertEqual(debt, [], "\n".join(debt))

    def test_false_marketing_and_patch_markers_are_absent(self):
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                UI_ROOT / "premium_preview.py",
                UI_ROOT / "hatirlatici_app.py",
                UI_ROOT / "hatirlatici_ultimate.py",
            )
        )
        for forbidden in (
            "Kullanıcı Kullanıcı",
            "Premium Hatırlatıcı",
            "CANLI VERİ",
            "install_premium",
            "install_guided",
        ):
            self.assertNotIn(forbidden, sources)

        language_classes = []
        forbidden_language_classes = []
        for path in UI_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if node.name == "LanguageMenuButton":
                    language_classes.append(path.name)
                if node.name == "MainLanguageButton":
                    forbidden_language_classes.append(path.name)
        self.assertEqual(language_classes, ["language_menu.py"])
        self.assertEqual(forbidden_language_classes, [])


class SingleInstanceRaceTests(unittest.TestCase):
    def test_live_owner_lock_prevents_unlink_when_probe_temporarily_fails(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        self.assertEqual(
            hatirlatici_ultimate.SINGLE_INSTANCE_OWNER_LOCK,
            app_identity.SINGLE_INSTANCE_OWNER_LOCK,
        )
        with tempfile.TemporaryDirectory() as directory:
            previous = {
                key: os.environ.get(key)
                for key in (
                    "XDG_CONFIG_HOME",
                    "XDG_DATA_HOME",
                    "XDG_STATE_HOME",
                )
            }
            root = Path(directory)
            os.environ["XDG_CONFIG_HOME"] = str(root / "config")
            os.environ["XDG_DATA_HOME"] = str(root / "data")
            os.environ["XDG_STATE_HOME"] = str(root / "state")
            server_name = "hatirlatici-live-" + uuid.uuid4().hex
            try:
                owner, forwarded = hatirlatici_ultimate.acquire_single_instance(
                    server_name,
                    b"raise",
                )
                self.assertIsNotNone(owner)
                self.assertFalse(forwarded)
                with mock.patch.object(
                    hatirlatici_ultimate,
                    "_forward_to_existing_instance",
                    return_value=False,
                ):
                    contender, contender_forwarded = (
                        hatirlatici_ultimate.acquire_single_instance(
                            server_name,
                            b"raise",
                        )
                    )
                self.assertIsNone(contender)
                self.assertFalse(contender_forwarded)
                self.assertTrue(owner.isListening())
            finally:
                if "owner" in locals() and owner is not None:
                    handle = owner._lifetime_lock_handle
                    owner.close()
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
                QLocalServer.removeServer(server_name)
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_concurrent_launches_choose_exactly_one_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = dict(os.environ)
            env.update(
                {
                    "XDG_CONFIG_HOME": str(root / "config"),
                    "XDG_DATA_HOME": str(root / "data"),
                    "XDG_STATE_HOME": str(root / "state"),
                    "QT_QPA_PLATFORM": "offscreen",
                    "PYTHONPATH": os.pathsep.join((str(ROOT), str(UI_ROOT))),
                }
            )
            server_name = "hatirlatici-test-" + uuid.uuid4().hex
            start_at = time.time() + 0.8
            code = (
                "import sys,time; "
                "from PyQt6.QtCore import QCoreApplication; "
                "from hatirlatici_ultimate import acquire_single_instance; "
                "app=QCoreApplication([]); "
                "target=float(sys.argv[2]); "
                "time.sleep(max(0,target-time.time())); "
                "server,forwarded=acquire_single_instance(sys.argv[1],b'raise'); "
                "print('FORWARDED' if forwarded else 'OWNER' if server else 'FAILED',flush=True); "
                "time.sleep(1.5 if server else 0)"
            )
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", code, server_name, str(start_at)],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for _ in range(6)
            ]
            results = [
                process.communicate(timeout=15)
                for process in processes
            ]
            statuses = []
            for process, (stdout, stderr) in zip(processes, results):
                self.assertEqual(process.returncode, 0, stderr)
                statuses.append(stdout.strip())

            self.assertEqual(statuses.count("OWNER"), 1, statuses)
            self.assertEqual(statuses.count("FORWARDED"), 5, statuses)
            self.assertNotIn("FAILED", statuses)
            QLocalServer.removeServer(server_name)


class MainUiGeometryGateTests(unittest.TestCase):
    def test_required_language_size_scale_matrix(self):
        gate = ROOT / "tools" / "main_ui_geometry_gate.py"
        for scale in ("1.0", "1.25", "1.5"):
            with self.subTest(scale=scale):
                env = dict(os.environ)
                env.pop("HATIRLATICI_MAIN_GEOMETRY_CODE_ROOT", None)
                env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(UI_ROOT)))
                result = subprocess.run(
                    [sys.executable, str(gate), "--scale", scale],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                    check=False,
                )
                self.assertIn("MAIN_UI_GEOMETRY_CASES=120", result.stdout)
                self.assertIn("MAIN_UI_GEOMETRY_FAILURES=0", result.stdout)
                self.assertIn("MAIN_UI_GEOMETRY_GATE=PASS", result.stdout)
                self.assertIn("MAIN_UI_CODE_ROOT_SOURCE=CHECKOUT", result.stdout)
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_invalid_installed_code_root_fails_closed(self):
        gate = ROOT / "tools" / "main_ui_geometry_gate.py"
        env = dict(os.environ)
        env["HATIRLATICI_MAIN_GEOMETRY_CODE_ROOT"] = (
            "/definitely/missing/hatirlatici"
        )
        result = subprocess.run(
            [sys.executable, str(gate), "--scale", "1.0"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 41, result.stdout)
        self.assertIn("MAIN_UI_GEOMETRY_GATE=FAIL_INVALID_CODE_ROOT", result.stdout)


if __name__ == "__main__":
    unittest.main()
