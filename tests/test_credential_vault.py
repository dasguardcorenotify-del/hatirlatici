import json
import os
import tempfile
import unittest
from pathlib import Path


import credential_vault
import runtime_config


def _master_one() -> bytes:
    return (
        b"vault-test-master-"
        + b"A" * 32
    )


def _master_two() -> bytes:
    return (
        b"vault-test-master-"
        + b"B" * 32
    )


def _credential() -> str:
    return (
        "smtp-"
        + "credential-"
        + "test-value-9347"
    )


class CredentialVaultTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        base = Path(
            self.temp.name
        )

        self.previous = {}

        for key in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
        ):
            self.previous[
                key
            ] = os.environ.get(
                key
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

    def test_key_is_256_bit(self):
        key = (
            credential_vault
            .derive_key(
                _master_one()
            )
        )

        self.assertEqual(
            len(key),
            32,
        )

    def test_encrypt_decrypt_roundtrip(self):
        value = (
            _credential()
        )

        credential_vault.store_smtp_credential(
            value,
            master_secret_provider=(
                _master_one
            ),
        )

        loaded = (
            credential_vault
            .load_smtp_credential(
                master_secret_provider=(
                    _master_one
                ),
            )
        )

        self.assertEqual(
            loaded,
            value,
        )

    def test_plaintext_not_on_disk(self):
        value = (
            _credential()
        )

        credential_vault.store_smtp_credential(
            value,
            master_secret_provider=(
                _master_one
            ),
        )

        raw = (
            runtime_config
            .credential_vault_path()
            .read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            value,
            raw,
        )

        payload = json.loads(
            raw
        )

        self.assertEqual(
            payload[
                "cipher"
            ],
            "AES-256-GCM",
        )

    def test_file_permission_0600(self):
        credential_vault.store_smtp_credential(
            _credential(),
            master_secret_provider=(
                _master_one
            ),
        )

        mode = (
            runtime_config
            .credential_vault_path()
            .stat()
            .st_mode
            & 0o777
        )

        self.assertEqual(
            mode,
            0o600,
        )

    def test_wrong_key_fails(self):
        credential_vault.store_smtp_credential(
            _credential(),
            master_secret_provider=(
                _master_one
            ),
        )

        with self.assertRaises(
            credential_vault
            .CredentialDecryptError
        ):
            (
                credential_vault
                .load_smtp_credential(
                    master_secret_provider=(
                        _master_two
                    ),
                )
            )

    def test_tamper_fails(self):
        credential_vault.store_smtp_credential(
            _credential(),
            master_secret_provider=(
                _master_one
            ),
        )

        path = (
            runtime_config
            .credential_vault_path()
        )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        ciphertext = (
            payload[
                "ciphertext"
            ]
        )

        payload[
            "ciphertext"
        ] = (
            (
                "A"
                if ciphertext[0]
                != "A"
                else "B"
            )
            + ciphertext[1:]
        )

        path.write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )

        with self.assertRaises(
            credential_vault
            .CredentialVaultError
        ):
            (
                credential_vault
                .load_smtp_credential(
                    master_secret_provider=(
                        _master_one
                    ),
                )
            )

    def test_delete(self):
        credential_vault.store_smtp_credential(
            _credential(),
            master_secret_provider=(
                _master_one
            ),
        )

        self.assertTrue(
            credential_vault
            .has_smtp_credential()
        )

        credential_vault.delete_smtp_credential()

        self.assertFalse(
            credential_vault
            .has_smtp_credential()
        )


if __name__ == "__main__":
    unittest.main()
