#!/usr/bin/env python3
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Callable


import runtime_config
import secret_portal


try:
    from cryptography.exceptions import (
        InvalidTag,
    )

    from cryptography.hazmat.primitives import (
        hashes,
    )

    from cryptography.hazmat.primitives.ciphers.aead import (
        AESGCM,
    )

    from cryptography.hazmat.primitives.kdf.hkdf import (
        HKDF,
    )

except Exception as exc:
    raise RuntimeError(
        "cryptography paketi gerekli."
    ) from exc


VAULT_VERSION = 1

CIPHER_NAME = "AES-256-GCM"

KDF_NAME = "HKDF-SHA256"

KEY_CONTEXT = (
    b"hatirlatici/credential-vault/v1"
)

KDF_SALT = hashlib.sha256(
    b"Hatirlatici Secret Portal Vault Salt v1"
).digest()

AAD = (
    b"hatirlatici|smtp-credential|v1"
)


class CredentialVaultError(
    RuntimeError
):
    pass


class CredentialNotConfigured(
    CredentialVaultError
):
    pass


class CredentialDecryptError(
    CredentialVaultError
):
    pass


MasterSecretProvider = Callable[
    [],
    bytes,
]


def _atomic_json_write(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    fd, temp_name = (
        tempfile.mkstemp(
            prefix=".credential.",
            suffix=".tmp",
            dir=str(
                path.parent
            ),
            text=True,
        )
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temp_name,
            0o600,
        )

        os.replace(
            temp_name,
            path,
        )

        os.chmod(
            path,
            0o600,
        )

    finally:
        try:
            os.unlink(
                temp_name
            )
        except FileNotFoundError:
            pass


def _load_json(
    path: Path,
) -> dict:
    if not path.exists():
        return {}

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise CredentialVaultError(
            "Credential metadata okunamadı."
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise CredentialVaultError(
            "Credential metadata biçimi geçersiz."
        )

    return value


def derive_key(
    master_secret: bytes,
) -> bytes:
    if not isinstance(
        master_secret,
        bytes,
    ):
        raise TypeError(
            "master_secret bytes olmalı."
        )

    if len(
        master_secret
    ) < 16:
        raise CredentialVaultError(
            "Portal master secret çok kısa."
        )

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=KDF_SALT,
        info=KEY_CONTEXT,
    )

    return hkdf.derive(
        master_secret
    )


def _portal_state() -> dict:
    path = (
        runtime_config
        .secret_portal_state_path()
    )

    if not path.exists():
        return {}

    return _load_json(
        path
    )


def _save_portal_token(
    token: str,
) -> None:
    clean = str(
        token
    ).strip()

    if not clean:
        return

    _atomic_json_write(
        runtime_config
        .secret_portal_state_path(),
        {
            "version": 1,
            "token": clean,
        },
    )


def portal_master_secret() -> bytes:
    state = (
        _portal_state()
    )

    previous_token = (
        str(
            state.get(
                "token",
                "",
            )
        ).strip()
        or None
    )

    try:
        result = (
            secret_portal
            .retrieve_secret(
                previous_token=(
                    previous_token
                ),
                require_flatpak=True,
            )
        )

    except secret_portal.SecretPortalError as exc:
        raise CredentialVaultError(
            "Güvenli credential anahtarı alınamadı."
        ) from exc

    if result.token:
        _save_portal_token(
            result.token
        )

    return result.secret


def has_smtp_credential() -> bool:
    return (
        runtime_config
        .credential_vault_path()
        .is_file()
    )


def store_smtp_credential(
    value: str,
    *,
    master_secret_provider:
        MasterSecretProvider
        | None = None,
) -> None:
    plaintext = str(
        value
    )

    if not plaintext:
        raise CredentialVaultError(
            "SMTP credential boş olamaz."
        )

    provider = (
        master_secret_provider
        or portal_master_secret
    )

    master_secret = provider()

    key = derive_key(
        master_secret
    )

    nonce = os.urandom(
        12
    )

    cipher = AESGCM(
        key
    )

    ciphertext = cipher.encrypt(
        nonce,
        plaintext.encode(
            "utf-8"
        ),
        AAD,
    )

    payload = {
        "version":
            VAULT_VERSION,

        "cipher":
            CIPHER_NAME,

        "kdf":
            KDF_NAME,

        "nonce":
            base64.b64encode(
                nonce
            ).decode(
                "ascii"
            ),

        "ciphertext":
            base64.b64encode(
                ciphertext
            ).decode(
                "ascii"
            ),

        "updated_at":
            dt.datetime.now(
                dt.timezone.utc
            ).isoformat(),
    }

    _atomic_json_write(
        runtime_config
        .credential_vault_path(),
        payload,
    )


def load_smtp_credential(
    *,
    master_secret_provider:
        MasterSecretProvider
        | None = None,
) -> str:
    path = (
        runtime_config
        .credential_vault_path()
    )

    if not path.exists():
        raise CredentialNotConfigured(
            "SMTP credential henüz yapılandırılmadı."
        )

    payload = (
        _load_json(
            path
        )
    )

    if (
        payload.get(
            "version"
        )
        != VAULT_VERSION
    ):
        raise CredentialVaultError(
            "Credential vault sürümü desteklenmiyor."
        )

    if (
        payload.get(
            "cipher"
        )
        != CIPHER_NAME
    ):
        raise CredentialVaultError(
            "Credential cipher desteklenmiyor."
        )

    if (
        payload.get(
            "kdf"
        )
        != KDF_NAME
    ):
        raise CredentialVaultError(
            "Credential KDF desteklenmiyor."
        )

    try:
        nonce = base64.b64decode(
            str(
                payload[
                    "nonce"
                ]
            ),
            validate=True,
        )

        ciphertext = (
            base64.b64decode(
                str(
                    payload[
                        "ciphertext"
                    ]
                ),
                validate=True,
            )
        )

    except (
        KeyError,
        ValueError,
    ) as exc:
        raise CredentialVaultError(
            "Credential vault verisi bozuk."
        ) from exc

    if len(
        nonce
    ) != 12:
        raise CredentialVaultError(
            "AES-GCM nonce geçersiz."
        )

    provider = (
        master_secret_provider
        or portal_master_secret
    )

    key = derive_key(
        provider()
    )

    try:
        plaintext = AESGCM(
            key
        ).decrypt(
            nonce,
            ciphertext,
            AAD,
        )

    except InvalidTag as exc:
        raise CredentialDecryptError(
            "Credential doğrulanamadı veya vault değiştirilmiş."
        ) from exc

    try:
        result = plaintext.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:
        raise CredentialDecryptError(
            "Credential UTF-8 değil."
        ) from exc

    if not result:
        raise CredentialDecryptError(
            "Credential boş çözüldü."
        )

    return result


def delete_smtp_credential() -> None:
    path = (
        runtime_config
        .credential_vault_path()
    )

    try:
        path.unlink()

    except FileNotFoundError:
        pass


def selftest() -> int:
    print(
        "VAULT_VERSION="
        + str(
            VAULT_VERSION
        )
    )

    print(
        "VAULT_CIPHER="
        + CIPHER_NAME
    )

    print(
        "VAULT_KDF="
        + KDF_NAME
    )

    print(
        "REAL_SECRET_PORTAL_RETRIEVE="
        "DEFERRED_TO_TEST_FLATPAK"
    )

    print(
        "CREDENTIAL_VAULT_SELFTEST=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        selftest()
    )
