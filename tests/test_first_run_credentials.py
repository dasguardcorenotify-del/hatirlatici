import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
)


import credential_vault
import runtime_config
from first_run_setup import (
    GuidedFirstRunDialog,
)


def _email(
    local: str,
) -> str:
    return (
        local
        + "@"
        + "example.invalid"
    )


class FirstRunCredentialTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        base = Path(
            self.temp.name
        )

        self.previous = {}

        for name in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
        ):
            self.previous[
                name
            ] = os.environ.get(
                name
            )

        os.environ[
            "XDG_CONFIG_HOME"
        ] = str(
            base / "config"
        )

        os.environ[
            "XDG_DATA_HOME"
        ] = str(
            base / "data"
        )

        os.environ[
            "XDG_STATE_HOME"
        ] = str(
            base / "state"
        )

    def tearDown(self):
        for key, value in (
            self.previous.items()
        ):
            if value is None:
                os.environ.pop(
                    key,
                    None,
                )
            else:
                os.environ[
                    key
                ] = value

        self.temp.cleanup()

    def configured_dialog(
        self,
    ):
        dialog = GuidedFirstRunDialog()

        dialog.name_edit.setText(
            "Test Kullanıcısı"
        )

        dialog._set_channel("email")

        dialog._set_provider("gmail")

        dialog.from_email.setText(
            _email(
                "sender"
            )
        )

        dialog.to_email.setText(
            _email(
                "receiver"
            )
        )

        return dialog

    def test_secret_field_is_masked(self):
        dialog = (
            self.configured_dialog()
        )

        self.assertEqual(
            dialog.gmail_secret_edit.echoMode(),
            QLineEdit.EchoMode.Password,
        )

        dialog.reject()

    def test_secret_not_in_payload(self):
        dialog = (
            self.configured_dialog()
        )

        dialog.gmail_secret_edit.setText(
            "fake-app-secret"
        )

        payload = (
            dialog.collect_payload()
        )

        self.assertFalse(
            any(
                "pass"
                in str(key).lower()
                or "secret"
                in str(key).lower()
                for key
                in payload.keys()
            )
        )

        self.assertNotIn(
            "fake-app-secret",
            repr(payload),
        )

        dialog.reject()

    def test_save_uses_vault_not_settings(
        self,
    ):
        dialog = (
            self.configured_dialog()
        )

        entered = (
            "fake-app-secret-3291"
        )

        dialog.gmail_secret_edit.setText(
            entered
        )

        with (
            mock.patch.object(
                credential_vault,
                "store_smtp_credential",
            ) as store,
            mock.patch.object(
                credential_vault,
                "has_smtp_credential",
                return_value=True,
            ),
        ):
            dialog._save()

        store.assert_called_once_with(
            entered
        )

        settings_text = (
            runtime_config
            .settings_path()
            .read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            entered,
            settings_text,
        )

        self.assertEqual(
            dialog.gmail_secret_edit.text(),
            "",
        )

        settings = (
            runtime_config
            .load_settings()
        )

        self.assertTrue(
            settings[
                "email_ready"
            ]
        )

    def test_existing_vault_allows_blank_reentry(
        self,
    ):
        dialog = (
            self.configured_dialog()
        )

        self.assertEqual(
            dialog.gmail_secret_edit.text(),
            "",
        )

        with (
            mock.patch.object(
                credential_vault,
                "has_smtp_credential",
                return_value=True,
            ),
            mock.patch.object(
                credential_vault,
                "store_smtp_credential",
            ) as store,
        ):
            dialog._save()

        store.assert_not_called()

        settings = (
            runtime_config
            .load_settings()
        )

        self.assertTrue(
            settings[
                "email_ready"
            ]
        )


if __name__ == "__main__":
    unittest.main()
