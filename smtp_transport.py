#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import errno
import hashlib
import socket
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import (
    format_datetime,
    parseaddr,
)
from enum import Enum


import credential_vault
import l10n
import runtime_config


SMTP_TIMEOUT_SECONDS = 20


class MailErrorCode(
    str,
    Enum,
):
    DNS = "dns"
    TIMEOUT = "timeout"
    TLS = "tls"
    AUTH = "auth"
    INVALID_SENDER = "invalid_sender"
    RECIPIENT_REFUSED = "recipient_refused"
    OFFLINE = "offline"
    GENERIC = "generic"


_MESSAGE_KEY_BY_CODE = {
    MailErrorCode.DNS:
        "smtp_error_dns",

    MailErrorCode.TIMEOUT:
        "smtp_error_timeout",

    MailErrorCode.TLS:
        "smtp_error_tls",

    MailErrorCode.AUTH:
        "smtp_error_auth",

    MailErrorCode.INVALID_SENDER:
        "smtp_error_invalid_sender",

    MailErrorCode.RECIPIENT_REFUSED:
        "smtp_error_recipient_refused",

    MailErrorCode.OFFLINE:
        "smtp_error_offline",

    MailErrorCode.GENERIC:
        "smtp_error_generic",
}


def _current_language() -> str:
    try:
        value = (
            runtime_config
            .load_settings()
            .get(
                "language",
                "en",
            )
        )
    except Exception:
        value = "en"

    return l10n.normalize_language(
        value
    )


def mail_error_message(
    code: MailErrorCode | str,
    language: str | None = None,
) -> str:
    try:
        normalized = MailErrorCode(
            code
        )
    except (
        TypeError,
        ValueError,
    ):
        normalized = (
            MailErrorCode.GENERIC
        )

    selected_language = (
        l10n.normalize_language(
            language
        )
        if language is not None
        else _current_language()
    )

    return l10n.text(
        _MESSAGE_KEY_BY_CODE[
            normalized
        ],
        selected_language,
    )


class MailTransportError(
    RuntimeError
):
    def __init__(
        self,
        code: MailErrorCode | str = (
            MailErrorCode.GENERIC
        ),
        *,
        language: str | None = None,
    ) -> None:
        try:
            normalized = MailErrorCode(
                code
            )
        except (
            TypeError,
            ValueError,
        ):
            normalized = (
                MailErrorCode.GENERIC
            )

        self.code = normalized.value
        self.message_key = (
            _MESSAGE_KEY_BY_CODE[
                normalized
            ]
        )
        self.language = (
            l10n.normalize_language(
                language
            )
            if language is not None
            else _current_language()
        )

        super().__init__(
            mail_error_message(
                normalized,
                self.language,
            )
        )


class MailConfigurationError(
    MailTransportError
):
    pass


@dataclass(
    frozen=True
)
class SMTPConfig:
    provider: str
    host: str
    port: int
    username: str
    from_email: str
    to_email: str
    implicit_tls: bool


def _clean_email(
    value: object,
    *,
    error_code: MailErrorCode,
    language: str,
) -> str:
    text = str(
        value or ""
    ).strip()

    name, address = parseaddr(
        text
    )

    if (
        name
        or not address
        or address != text
        or "@" not in address
    ):
        raise MailConfigurationError(
            error_code,
            language=language,
        )

    local, _, domain = (
        address.rpartition("@")
    )

    if (
        not local
        or not domain
        or "." not in domain
    ):
        raise MailConfigurationError(
            error_code,
            language=language,
        )

    return address


def load_config() -> SMTPConfig:
    settings = (
        runtime_config
        .load_settings()
    )

    language = l10n.normalize_language(
        settings.get(
            "language",
            "en",
        )
    )

    if not bool(
        settings.get(
            "email_enabled",
            False,
        )
    ):
        raise MailConfigurationError(
            MailErrorCode.GENERIC,
            language=language,
        )

    if not bool(
        settings.get(
            "email_ready",
            False,
        )
    ):
        raise MailConfigurationError(
            MailErrorCode.AUTH,
            language=language,
        )

    provider = str(
        settings.get(
            "smtp_provider",
            "",
        )
    ).strip().lower()

    if provider not in {
        "gmail",
        "custom",
    }:
        raise MailConfigurationError(
            MailErrorCode.GENERIC,
            language=language,
        )

    from_email = _clean_email(
        settings.get(
            "mail_from_email",
            "",
        ),
        error_code=(
            MailErrorCode
            .INVALID_SENDER
        ),
        language=language,
    )

    to_email = _clean_email(
        settings.get(
            "mail_to_email",
            "",
        ),
        error_code=(
            MailErrorCode
            .RECIPIENT_REFUSED
        ),
        language=language,
    )

    if provider == "gmail":
        host = "smtp.gmail.com"
        port = 587
        implicit_tls = False

    else:
        host = str(
            settings.get(
                "smtp_host",
                "",
            )
        ).strip()

        if not host:
            raise MailConfigurationError(
                MailErrorCode.GENERIC,
                language=language,
            )

        try:
            port = int(
                settings.get(
                    "smtp_port",
                    587,
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            raise MailConfigurationError(
                MailErrorCode.GENERIC,
                language=language,
            ) from None

        if not (
            1
            <= port
            <= 65535
        ):
            raise MailConfigurationError(
                MailErrorCode.GENERIC,
                language=language,
            )

        raw_security = str(
            settings.get(
                "smtp_security",
                "",
            )
        ).strip().lower()

        # Migration compatibility: profiles created before setup schema v2
        # expressed the mode through port 465. New profiles store the user's
        # explicit secure choice.
        if not raw_security:
            raw_security = (
                "implicit_tls"
                if port == 465
                else "starttls"
            )

        if raw_security not in {
            "starttls",
            "implicit_tls",
        }:
            raise MailConfigurationError(
                MailErrorCode.TLS,
                language=language,
            )

        implicit_tls = (
            raw_security
            == "implicit_tls"
        )

    username = str(
        settings.get(
            "smtp_username",
            "",
        )
    ).strip()

    if not username:
        username = from_email

    return SMTPConfig(
        provider=provider,
        host=host,
        port=port,
        username=username,
        from_email=from_email,
        to_email=to_email,
        implicit_tls=implicit_tls,
    )


def tls_context() -> ssl.SSLContext:
    context = (
        ssl.create_default_context()
    )

    try:
        context.minimum_version = (
            ssl.TLSVersion.TLSv1_2
        )
    except AttributeError:
        pass

    return context


_OFFLINE_ERRNOS = frozenset(
    value
    for value in (
        getattr(
            errno,
            name,
            None,
        )
        for name in (
            "ENETDOWN",
            "ENETUNREACH",
            "ENONET",
            "EHOSTDOWN",
            "EHOSTUNREACH",
        )
    )
    if isinstance(
        value,
        int,
    )
)


def classify_mail_error(
    error: BaseException,
) -> MailErrorCode:
    # SMTP protocol exceptions inherit OSError in the standard library,
    # so the specific safe categories must be checked before errno-based
    # network classification.
    if isinstance(
        error,
        smtplib.SMTPAuthenticationError,
    ):
        return MailErrorCode.AUTH

    if isinstance(
        error,
        smtplib.SMTPSenderRefused,
    ):
        return (
            MailErrorCode
            .INVALID_SENDER
        )

    if isinstance(
        error,
        smtplib.SMTPRecipientsRefused,
    ):
        return (
            MailErrorCode
            .RECIPIENT_REFUSED
        )

    if isinstance(
        error,
        (
            ssl.SSLError,
            smtplib
            .SMTPNotSupportedError,
        ),
    ):
        return MailErrorCode.TLS

    if isinstance(
        error,
        socket.gaierror,
    ):
        return MailErrorCode.DNS

    if isinstance(
        error,
        (
            TimeoutError,
            socket.timeout,
        ),
    ):
        return MailErrorCode.TIMEOUT

    if (
        isinstance(
            error,
            OSError,
        )
        and getattr(
            error,
            "errno",
            None,
        ) in _OFFLINE_ERRNOS
    ):
        return MailErrorCode.OFFLINE

    return MailErrorCode.GENERIC


def deterministic_message_id(
    *,
    pair_id: str,
    scheduled_value: str,
    from_email: str,
) -> str:
    material = (
        str(pair_id)
        + "\0"
        + str(scheduled_value)
        + "\0"
        + str(from_email)
    ).encode(
        "utf-8"
    )

    digest = hashlib.sha256(
        material
    ).hexdigest()[:32]

    domain = (
        from_email
        .rpartition("@")[2]
        .strip()
        or "hatirlatici.invalid"
    )

    return (
        "<hatirlatici-"
        + digest
        + "@"
        + domain
        + ">"
    )


def build_message(
    *,
    config: SMTPConfig,
    subject: str,
    body: str,
    pair_id: str,
    scheduled_value: str,
) -> EmailMessage:
    default_subject = l10n.text(
        "reminder_default_title",
        _current_language(),
    )

    clean_subject = (
        " ".join(
            str(
                subject
                or default_subject
            )
            .replace(
                "\r",
                " ",
            )
            .replace(
                "\n",
                " ",
            )
            .split()
        )[:200]
        or default_subject
    )

    message = EmailMessage()

    message[
        "From"
    ] = config.from_email

    message[
        "To"
    ] = config.to_email

    message[
        "Subject"
    ] = clean_subject

    message[
        "Date"
    ] = format_datetime(
        dt.datetime.now(
            dt.timezone.utc
        )
    )

    message[
        "Message-ID"
    ] = deterministic_message_id(
        pair_id=pair_id,
        scheduled_value=scheduled_value,
        from_email=config.from_email,
    )

    message.set_content(
        str(
            body or ""
        ),
        charset="utf-8",
    )

    return message


def send_reminder(
    *,
    subject: str,
    body: str,
    pair_id: str,
    scheduled_value: str,
) -> None:
    config = load_config()

    try:
        credential = (
            credential_vault
            .load_smtp_credential()
        )

    except (
        credential_vault
        .CredentialVaultError
    ):
        raise MailTransportError(
            MailErrorCode.AUTH
        ) from None

    if not credential:
        raise MailTransportError(
            MailErrorCode.AUTH
        )

    message = build_message(
        config=config,
        subject=subject,
        body=body,
        pair_id=pair_id,
        scheduled_value=scheduled_value,
    )

    try:
        context = tls_context()

        if config.implicit_tls:
            with smtplib.SMTP_SSL(
                config.host,
                config.port,
                timeout=(
                    SMTP_TIMEOUT_SECONDS
                ),
                context=context,
            ) as client:
                client.ehlo()

                client.login(
                    config.username,
                    credential,
                )

                client.send_message(
                    message,
                    from_addr=(
                        config.from_email
                    ),
                    to_addrs=[
                        config.to_email,
                    ],
                )

        else:
            with smtplib.SMTP(
                config.host,
                config.port,
                timeout=(
                    SMTP_TIMEOUT_SECONDS
                ),
            ) as client:
                client.ehlo()

                client.starttls(
                    context=context
                )

                # RFC/STDLIB önerisi:
                # TLS sonrası EHLO yeniden yapılır.
                client.ehlo()

                client.login(
                    config.username,
                    credential,
                )

                client.send_message(
                    message,
                    from_addr=(
                        config.from_email
                    ),
                    to_addrs=[
                        config.to_email,
                    ],
                )

    except (
        smtplib.SMTPException,
        OSError,
        ssl.SSLError,
    ) as exc:
        # The exception, server response, addresses, credential and
        # reminder content never become part of the user-facing error.
        raise MailTransportError(
            classify_mail_error(
                exc
            )
        ) from None

    finally:
        # Python str nesnesi güvenilir biçimde
        # RAM'de sıfırlanamaz. Referansı mümkün
        # olan en kısa sürede bırakıyoruz.
        credential = ""


def selftest() -> int:
    context = tls_context()

    assert context.check_hostname

    print(
        "SMTP_LIBRARY=smtplib"
    )

    print(
        "SMTP_TLS_CONTEXT=PASS"
    )

    print(
        "SMTP_TIMEOUT_SECONDS="
        + str(
            SMTP_TIMEOUT_SECONDS
        )
    )

    print(
        "SMTP_TRANSPORT_SELFTEST=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        selftest()
    )
