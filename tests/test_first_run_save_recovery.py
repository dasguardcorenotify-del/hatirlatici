"""Real Qt/model tests, synthetic settings failures and ciphertext only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PyQt6.QtWidgets import QApplication, QDialog
import credential_vault
import first_run_setup
import l10n
import runtime_config
import setup_model
import setup_persistence


class FirstRunSaveRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        environment = {key: str(root / key.lower()) for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")}
        patch = mock.patch.dict(os.environ, environment)
        patch.start()
        self.addCleanup(patch.stop)
        self.dialogs = []
        self.addCleanup(self.close_dialogs)

    def close_dialogs(self):
        for dialog in self.dialogs:
            dialog.reject()
            dialog.deleteLater()
        self.app.processEvents()

    def make_dialog(self, **options):
        dialog = first_run_setup.GuidedFirstRunDialog(force=True, **options)
        self.dialogs.append(dialog)
        dialog.name_edit.setText("QA")
        return dialog

    def profile(self, **extra):
        value = {"profile_name": "QA", "language": "en", "setup_complete": True,
                 "default_channel": "email", "email_enabled": True, "smtp_provider": "custom",
                 "smtp_host": "mail.example.invalid", "smtp_port": 465, "smtp_security": "implicit_tls",
                 "smtp_username": "qa", "mail_from_email": "sender@example.invalid", "mail_to_email": "receiver@example.invalid"}
        value.update(extra)
        runtime_config.save_settings(value)
        return value

    def put_vault(self, value=b"synthetic prior ciphertext"):
        path = runtime_config.credential_vault_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(value)
        path.chmod(0o600)
        return path

    def test_saved_modes_survive_reopen_and_language_changes(self):
        for mode, port in (("implicit_tls", 465), ("starttls", 587)):
            with self.subTest(mode=mode):
                self.profile(smtp_security=mode, smtp_port=port)
                dialog = self.make_dialog(preview=True)
                for language in l10n.SUPPORTED_LANGUAGES:
                    dialog._apply_language(language)
                    self.assertEqual(dialog.custom_security.currentData(), mode)
                    self.assertEqual(dialog.collect_payload()["smtp_security"], mode)
                    self.assertEqual(dialog.custom_port.value(), port)

    def test_legacy_missing_mode_matches_transport_port_default(self):
        profile = self.profile()
        del profile["smtp_security"]
        for port, mode in ((465, "implicit_tls"), (587, "starttls")):
            profile["smtp_port"] = port
            runtime_config.save_settings(profile)
            dialog = self.make_dialog(preview=True)
            self.assertEqual(dialog.custom_security.currentData(), mode)

    def test_invalid_saved_security_requires_explicit_choice(self):
        self.profile(smtp_security="plaintext")
        dialog = self.make_dialog(preview=True)
        for language in l10n.SUPPORTED_LANGUAGES:
            dialog._apply_language(language)
            self.assertIsNone(dialog.custom_security.currentData())
            self.assertTrue(setup_model.validate_email(dialog.collect_payload(), language=language))

    def test_settings_error_is_caught_without_accept_or_raw_exception(self):
        dialog = self.make_dialog()
        dialog._set_channel("pc")
        for language in l10n.SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                dialog._apply_language(language)
                with mock.patch.object(runtime_config, "save_settings", side_effect=OSError("PRIVATE_DIAGNOSTIC")), mock.patch.object(dialog, "_show_notice") as notice:
                    dialog._save()
                self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)
                self.assertEqual(notice.call_args.args[1], dialog._t("setup_save_failed"))
                self.assertNotIn("PRIVATE_DIAGNOSTIC", repr(notice.call_args))
                self.assertEqual(dialog.name_edit.text(), "QA")
                self.assertTrue(dialog.next_button.isEnabled())

    def test_failed_settings_write_restores_replaced_vault_bytes(self):
        self.profile()
        before = runtime_config.settings_path().read_bytes()
        vault = self.put_vault()
        dialog = self.make_dialog()
        dialog.custom_secret_edit.setText("synthetic-entry")
        def store(_value):
            vault.write_bytes(b"synthetic replacement ciphertext")
        with mock.patch.object(credential_vault, "store_smtp_credential", side_effect=store), mock.patch.object(runtime_config, "save_settings", side_effect=OSError("synthetic")), mock.patch.object(dialog, "_show_notice"):
            dialog._save()
        self.assertEqual(vault.read_bytes(), b"synthetic prior ciphertext")
        self.assertEqual(runtime_config.settings_path().read_bytes(), before)
        self.assertEqual(dialog.custom_secret_edit.text(), "")
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_failed_settings_write_restores_deleted_vault(self):
        self.profile()
        before = runtime_config.settings_path().read_bytes()
        vault = self.put_vault()
        dialog = self.make_dialog()
        dialog._set_channel("pc")
        dialog.delete_credential.setChecked(True)
        with mock.patch.object(runtime_config, "save_settings", side_effect=OSError("synthetic")), mock.patch.object(dialog, "_show_notice"):
            dialog._save()
        self.assertEqual(vault.read_bytes(), b"synthetic prior ciphertext")
        self.assertEqual(runtime_config.settings_path().read_bytes(), before)

    def test_vault_oserror_is_safe_and_clears_password(self):
        self.profile()
        self.put_vault()
        dialog = self.make_dialog()
        dialog.custom_secret_edit.setText("synthetic-entry")
        with mock.patch.object(credential_vault, "store_smtp_credential", side_effect=OSError("PRIVATE_DIAGNOSTIC")), mock.patch.object(dialog, "_show_notice") as notice:
            dialog._save()
        self.assertNotIn("PRIVATE_DIAGNOSTIC", repr(notice.call_args))
        self.assertEqual(dialog.custom_secret_edit.text(), "")
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_retry_after_settings_failure_can_complete(self):
        dialog = self.make_dialog()
        dialog._set_channel("pc")
        with mock.patch.object(runtime_config, "save_settings", side_effect=OSError("synthetic")), mock.patch.object(dialog, "_show_notice"):
            dialog._save()
        dialog._save()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(runtime_config.load_settings()["setup_complete"])

    def test_preview_does_not_start_persistence(self):
        dialog = self.make_dialog(preview=True)
        with mock.patch.object(setup_persistence, "protect_setup_files") as guard, mock.patch.object(dialog, "_show_notice"):
            dialog._save()
        guard.assert_not_called()
        self.assertFalse(runtime_config.settings_path().exists())

    def test_reentrant_save_is_ignored(self):
        dialog = self.make_dialog()
        dialog._save_in_progress = True
        with mock.patch.object(runtime_config, "save_settings") as save, mock.patch.object(credential_vault, "store_smtp_credential") as store:
            dialog._save()
        save.assert_not_called()
        store.assert_not_called()

    def test_failed_rollback_has_distinct_notice(self):
        dialog = self.make_dialog()
        dialog._set_channel("pc")
        with mock.patch.object(setup_persistence, "protect_setup_files", side_effect=setup_persistence.SetupRollbackError("SETUP_ROLLBACK_FAILED")), mock.patch.object(dialog, "_show_notice") as notice:
            dialog._save()
        self.assertEqual(notice.call_args.args[1], dialog._t("setup_restore_failed"))
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
