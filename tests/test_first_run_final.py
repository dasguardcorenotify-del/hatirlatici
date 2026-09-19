import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit

import l10n
import runtime_config
from first_run_setup import ChoiceCard, GuidedFirstRunDialog


class FinalFirstRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.previous = {
            name: os.environ.get(name)
            for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")
        }
        os.environ["XDG_CONFIG_HOME"] = str(root / "config")
        os.environ["XDG_DATA_HOME"] = str(root / "data")
        os.environ["XDG_STATE_HOME"] = str(root / "state")

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp.cleanup()

    def dialog(self, **kwargs):
        dialog = GuidedFirstRunDialog(**kwargs)
        dialog.show()
        self.app.processEvents()
        return dialog

    def test_one_explicit_production_dialog(self):
        import first_run_setup

        dialogs = {
            value
            for value in vars(first_run_setup).values()
            if isinstance(value, type)
            and value.__module__ == first_run_setup.__name__
            and issubclass(value, QDialog)
        }
        self.assertEqual(dialogs, {GuidedFirstRunDialog, first_run_setup.NoticeDialog})
        self.assertEqual(GuidedFirstRunDialog.__mro__[1], QDialog)
        source = Path(first_run_setup.__file__).read_text(encoding="utf-8")
        self.assertNotIn("install_premium", source)
        self.assertNotIn("install_guided", source)

    def test_responsive_minimum_and_stable_footer(self):
        dialog = self.dialog()
        self.assertEqual((dialog.minimumWidth(), dialog.minimumHeight()), (960, 680))
        dialog.resize(960, 680)
        self.app.processEvents()
        self.assertEqual((dialog.width(), dialog.height()), (960, 680))
        self.assertEqual(dialog.pages.count(), 5)
        self.assertTrue(dialog.exit_button.isVisible())
        self.assertTrue(dialog.next_button.isVisible())
        dialog.close()

    def test_language_menu_is_single_and_live(self):
        dialog = self.dialog()
        menu = dialog.language_selector.menu()
        self.assertIsNotNone(menu)
        self.assertEqual([action.data() for action in menu.actions()], list(l10n.SUPPORTED_LANGUAGES))
        self.assertFalse(any(glyph in dialog.language_selector.text() for glyph in ("▾", "▼")))
        dialog.language_selector.select_language("de")
        self.app.processEvents()
        self.assertEqual(dialog.language, "de")
        self.assertIn("Ersteinrichtung", dialog.windowTitle())
        dialog.language_selector.select_language("ru")
        self.app.processEvents()
        self.assertIn("Первоначальная", dialog.windowTitle())
        dialog.close()

    def test_supported_system_locale_is_initial_language(self):
        root = Path(__file__).resolve().parent.parent
        code = (
            "import os,tempfile; from pathlib import Path; "
            "p=Path(tempfile.mkdtemp()); "
            "os.environ['XDG_CONFIG_HOME']=str(p/'c'); "
            "os.environ['XDG_DATA_HOME']=str(p/'d'); "
            "os.environ['XDG_STATE_HOME']=str(p/'s'); "
            "from PyQt6.QtWidgets import QApplication; "
            "from first_run_setup import GuidedFirstRunDialog; "
            "a=QApplication([]); d=GuidedFirstRunDialog(); print(d.language)"
        )
        env = dict(os.environ)
        env.update(
            {
                "LANG": "de_DE.UTF-8",
                "LANGUAGE": "de",
                "LC_ALL": "de_DE.UTF-8",
                "QT_QPA_PLATFORM": "offscreen",
                "PYTHONPATH": os.pathsep.join((str(root), str(root / "ui_v2"))),
            }
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "de")

    def test_delivery_cards_are_accessible_without_unicode_hacks(self):
        dialog = self.dialog()
        for card in dialog.findChildren(ChoiceCard):
            self.assertEqual(card.focusPolicy(), Qt.FocusPolicy.StrongFocus)
            self.assertTrue(card.accessibleName())
            self.assertFalse(any(glyph in card.accessibleName() for glyph in ("▣", "◈")))
        dialog.close()

    def test_pc_only_skips_email_and_security(self):
        dialog = self.dialog()
        dialog.name_edit.setText("Test")
        dialog._set_channel("pc")
        dialog.pages.setCurrentIndex(1)
        dialog._go_next()
        self.assertEqual(dialog.pages.currentIndex(), 4)
        for index in (2, 3):
            frame, number, _title, subtitle = dialog.steps[index]
            self.assertEqual(frame.property("state"), "skipped")
            self.assertEqual(number.text(), "–")
            self.assertEqual(subtitle.text(), dialog._t("skipped"))
        self.assertEqual(dialog.review_rows[3][2].text(), dialog._t("skipped"))
        self.assertEqual(dialog.review_rows[4][2].text(), dialog._t("skipped"))
        dialog.close()

    def test_custom_smtp_skips_only_gmail_guide(self):
        dialog = self.dialog()
        dialog._set_channel("email")
        dialog._set_provider("custom")
        dialog.pages.setCurrentIndex(4)
        dialog._update_navigation()
        self.assertNotEqual(dialog.steps[2][0].property("state"), "skipped")
        self.assertEqual(dialog.steps[3][0].property("state"), "skipped")
        dialog._go_back()
        self.assertEqual(dialog.pages.currentIndex(), 2)
        dialog.close()

    def test_switching_from_pc_restores_active_step_copy(self):
        dialog = self.dialog()
        dialog.language_selector.select_language("es")
        dialog._set_channel("pc")
        self.assertEqual(dialog.steps[2][3].text(), dialog._t("skipped"))
        self.assertEqual(dialog.steps[3][3].text(), dialog._t("skipped"))
        dialog._set_channel("email")
        dialog._set_provider("gmail")
        dialog.pages.setCurrentIndex(3)
        dialog._update_navigation()
        self.assertEqual(dialog.steps[2][3].text(), dialog._t("step_email_sub"))
        self.assertEqual(dialog.steps[3][3].text(), dialog._t("step_security_sub"))
        dialog.close()

    def test_gmail_and_custom_secrets_are_masked_and_isolated(self):
        dialog = self.dialog()
        self.assertIsNot(dialog.gmail_secret_edit, dialog.custom_secret_edit)
        self.assertEqual(dialog.gmail_secret_edit.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(dialog.custom_secret_edit.echoMode(), QLineEdit.EchoMode.Password)
        dialog.gmail_secret_edit.setText("gmail-secret")
        dialog.custom_secret_edit.setText("custom-secret")
        self.assertNotIn("gmail-secret", repr(dialog.collect_payload()))
        self.assertNotIn("custom-secret", repr(dialog.collect_payload()))
        dialog.close()

    def test_gmail_transport_values_are_fixed_and_secure(self):
        dialog = self.dialog()
        dialog._set_channel("email")
        dialog._set_provider("gmail")
        payload = dialog.collect_payload()
        self.assertEqual(payload["smtp_host"], "smtp.gmail.com")
        self.assertEqual(payload["smtp_port"], 587)
        self.assertEqual(payload["smtp_security"], "starttls")
        self.assertEqual(dialog.GOOGLE_APP_PASSWORDS_URL, "https://myaccount.google.com/apppasswords")
        dialog.close()

    def test_all_labels_are_buddied_to_fields(self):
        dialog = self.dialog()
        pairs = (
            (dialog.name_label, dialog.name_edit),
            (dialog.language_label, dialog.language_selector),
            (dialog.gmail_from_label, dialog.from_email),
            (dialog.gmail_to_label, dialog.to_email),
            (dialog.custom_host_label, dialog.custom_host),
            (dialog.custom_port_label, dialog.custom_port),
            (dialog.custom_secret_label, dialog.custom_secret_edit),
            (dialog.gmail_secret_label, dialog.gmail_secret_edit),
        )
        for label, field in pairs:
            self.assertIs(label.buddy(), field)
        dialog.close()

    def test_preview_never_persists(self):
        dialog = self.dialog(preview=True)
        dialog.name_edit.setText("Preview")
        dialog._set_channel("pc")
        with mock.patch.object(dialog, "_show_notice") as notice:
            dialog._save()
        notice.assert_called_once()
        self.assertFalse(runtime_config.settings_path().exists())
        dialog.close()

    def test_existing_values_are_preserved_when_reopened(self):
        runtime_config.save_settings(
            {
                "setup_complete": True,
                "profile_name": "Ada",
                "language": "es",
                "default_channel": "pc",
                "email_enabled": False,
                "smtp_provider": "custom",
                "smtp_host": "mail.example.invalid",
                "smtp_port": 465,
                "future_key": "preserve-me",
            }
        )
        dialog = self.dialog(force=True)
        self.assertEqual(dialog.name_edit.text(), "Ada")
        self.assertEqual(dialog.language, "es")
        self.assertEqual(dialog.selected_channel, "pc")
        self.assertEqual(dialog.selected_provider, "custom")
        self.assertEqual(dialog.custom_host.text(), "mail.example.invalid")
        self.assertEqual(dialog.custom_port.value(), 465)
        dialog._save()
        saved = runtime_config.load_settings()
        self.assertEqual(saved["future_key"], "preserve-me")
        self.assertEqual(saved["profile_name"], "Ada")


if __name__ == "__main__":
    unittest.main()
