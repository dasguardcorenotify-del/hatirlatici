import errno
import os
import socket
import smtplib
import ssl
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest import mock


import runtime_config
import smtp_transport
import l10n


EVENTS = []


def _mail(
    local: str,
) -> str:
    return (
        local
        + "@"
        + "example.invalid"
    )


class FakeSMTP:
    def __init__(
        self,
        host,
        port,
        timeout=None,
        **kwargs,
    ):
        self.host = host
        self.port = port

        EVENTS.append(
            (
                "connect",
                host,
                port,
            )
        )

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        EVENTS.append(
            (
                "close",
            )
        )

    def ehlo(self):
        EVENTS.append(
            (
                "ehlo",
            )
        )

    def starttls(
        self,
        context=None,
    ):
        EVENTS.append(
            (
                "starttls",
            )
        )

    def login(
        self,
        username,
        password,
    ):
        EVENTS.append(
            (
                "login",
                username,
                password,
            )
        )

    def send_message(
        self,
        message,
        **kwargs,
    ):
        EVENTS.append(
            (
                "send",
                message[
                    "Message-ID"
                ],
            )
        )


class FakeSMTPSSL(
    FakeSMTP
):
    def __init__(
        self,
        host,
        port,
        timeout=None,
        context=None,
    ):
        super().__init__(
            host,
            port,
            timeout=timeout,
        )

        EVENTS.append(
            (
                "implicit_tls",
            )
        )


class AuthenticationFailureSMTP(
    FakeSMTP
):
    def login(
        self,
        username,
        password,
    ):
        raise (
            smtplib
            .SMTPAuthenticationError(
                535,
                b"private-server-response",
            )
        )


class SMTPTransportTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        root = Path(
            self.temp.name
        )

        self.old = {}

        for key in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
        ):
            self.old[
                key
            ] = os.environ.get(
                key
            )

        os.environ[
            "XDG_CONFIG_HOME"
        ] = str(
            root
            / "config"
        )

        os.environ[
            "XDG_DATA_HOME"
        ] = str(
            root
            / "data"
        )

        os.environ[
            "XDG_STATE_HOME"
        ] = str(
            root
            / "state"
        )

        EVENTS.clear()

    def tearDown(self):
        for key, value in (
            self.old.items()
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

    def save_gmail(self):
        runtime_config.save_settings(
            {
                "email_enabled":
                    True,

                "email_ready":
                    True,

                "mail_transport_v2_ready":
                    True,

                "smtp_provider":
                    "gmail",

                "smtp_username":
                    _mail(
                        "sender"
                    ),

                "mail_from_email":
                    _mail(
                        "sender"
                    ),

                "mail_to_email":
                    _mail(
                        "receiver"
                    ),
            }
        )

    def test_gmail_starttls_flow(self):
        self.save_gmail()

        fake_secret = (
            "fake-credential-4417"
        )

        with (
            mock.patch.object(
                smtp_transport
                .credential_vault,
                "load_smtp_credential",
                return_value=(
                    fake_secret
                ),
            ),
            mock.patch.object(
                smtp_transport
                .smtplib,
                "SMTP",
                FakeSMTP,
            ),
        ):
            smtp_transport.send_reminder(
                subject="Test",
                body="Body",
                pair_id="pair-a",
                scheduled_value=(
                    "2026-08-20 18:00"
                ),
            )

        self.assertIn(
            (
                "connect",
                "smtp.gmail.com",
                587,
            ),
            EVENTS,
        )

        self.assertIn(
            (
                "starttls",
            ),
            EVENTS,
        )

        self.assertIn(
            (
                "login",
                _mail(
                    "sender"
                ),
                fake_secret,
            ),
            EVENTS,
        )

        send_indexes = [
            index
            for index, item
            in enumerate(EVENTS)
            if item[0] == "send"
        ]

        tls_indexes = [
            index
            for index, item
            in enumerate(EVENTS)
            if item[0]
            == "starttls"
        ]

        self.assertTrue(
            tls_indexes[0]
            < send_indexes[0]
        )

    def test_custom_465_uses_implicit_tls(self):
        runtime_config.save_settings(
            {
                "email_enabled":
                    True,

                "email_ready":
                    True,

                "mail_transport_v2_ready":
                    True,

                "smtp_provider":
                    "custom",

                "smtp_host":
                    "smtp.example.invalid",

                "smtp_port":
                    465,

                "smtp_username":
                    "custom-user",

                "mail_from_email":
                    _mail(
                        "sender"
                    ),

                "mail_to_email":
                    _mail(
                        "receiver"
                    ),
            }
        )

        with (
            mock.patch.object(
                smtp_transport
                .credential_vault,
                "load_smtp_credential",
                return_value=(
                    "fake-custom-secret"
                ),
            ),
            mock.patch.object(
                smtp_transport
                .smtplib,
                "SMTP_SSL",
                FakeSMTPSSL,
            ),
        ):
            smtp_transport.send_reminder(
                subject="Test",
                body="Body",
                pair_id="pair-b",
                scheduled_value=(
                    "2026-08-20 18:01"
                ),
            )

        self.assertIn(
            (
                "implicit_tls",
            ),
            EVENTS,
        )

        self.assertNotIn(
            (
                "starttls",
            ),
            EVENTS,
        )

    def test_message_id_is_deterministic(self):
        self.save_gmail()

        config = (
            smtp_transport
            .load_config()
        )

        first = (
            smtp_transport
            .build_message(
                config=config,
                subject="Test",
                body="Body",
                pair_id="pair-x",
                scheduled_value=(
                    "2026-08-20 18:02"
                ),
            )
        )

        second = (
            smtp_transport
            .build_message(
                config=config,
                subject="Test",
                body="Body",
                pair_id="pair-x",
                scheduled_value=(
                    "2026-08-20 18:02"
                ),
            )
        )

        self.assertEqual(
            first["Message-ID"],
            second["Message-ID"],
        )

    def test_safe_error_classification(self):
        private = (
            "private-server-response"
        )

        cases = (
            (
                socket.gaierror(
                    -2,
                    private,
                ),
                smtp_transport
                .MailErrorCode.DNS,
            ),
            (
                TimeoutError(
                    private
                ),
                smtp_transport
                .MailErrorCode.TIMEOUT,
            ),
            (
                ssl.SSLError(
                    private
                ),
                smtp_transport
                .MailErrorCode.TLS,
            ),
            (
                smtplib
                .SMTPAuthenticationError(
                    535,
                    private.encode(),
                ),
                smtp_transport
                .MailErrorCode.AUTH,
            ),
            (
                smtplib
                .SMTPSenderRefused(
                    553,
                    private.encode(),
                    "private-sender@example.invalid",
                ),
                smtp_transport
                .MailErrorCode
                .INVALID_SENDER,
            ),
            (
                smtplib
                .SMTPRecipientsRefused(
                    {
                        "private-recipient@example.invalid":
                            (
                                550,
                                private.encode(),
                            ),
                    }
                ),
                smtp_transport
                .MailErrorCode
                .RECIPIENT_REFUSED,
            ),
            (
                OSError(
                    errno.ENETUNREACH,
                    private,
                ),
                smtp_transport
                .MailErrorCode.OFFLINE,
            ),
        )

        for error, expected in cases:
            with self.subTest(
                expected=expected.value
            ):
                code = (
                    smtp_transport
                    .classify_mail_error(
                        error
                    )
                )

                self.assertEqual(
                    code,
                    expected,
                )

                wrapped = (
                    smtp_transport
                    .MailTransportError(
                        code,
                        language="en",
                    )
                )

                self.assertEqual(
                    wrapped.code,
                    expected.value,
                )

                self.assertNotIn(
                    private,
                    str(wrapped),
                )

                self.assertNotIn(
                    "private-",
                    str(wrapped),
                )

    def test_safe_error_messages_are_localized_for_every_locale(
        self,
    ):
        for language in (
            l10n.SUPPORTED_LANGUAGES
        ):
            for code in (
                smtp_transport.MailErrorCode
            ):
                with self.subTest(
                    language=language,
                    code=code.value,
                ):
                    expected = l10n.text(
                        smtp_transport
                        ._MESSAGE_KEY_BY_CODE[
                            code
                        ],
                        language,
                    )

                    self.assertEqual(
                        smtp_transport
                        .mail_error_message(
                            code,
                            language,
                        ),
                        expected,
                    )

                    self.assertEqual(
                        str(
                            smtp_transport
                            .MailTransportError(
                                code,
                                language=language,
                            )
                        ),
                        expected,
                    )

    def test_send_error_has_no_server_response_or_traceback_chain(
        self,
    ):
        self.save_gmail()

        with (
            mock.patch.object(
                smtp_transport
                .credential_vault,
                "load_smtp_credential",
                return_value=(
                    "private-app-password"
                ),
            ),
            mock.patch.object(
                smtp_transport
                .smtplib,
                "SMTP",
                AuthenticationFailureSMTP,
            ),
            self.assertRaises(
                smtp_transport
                .MailTransportError
            ) as raised,
        ):
            smtp_transport.send_reminder(
                subject=(
                    "private reminder"
                ),
                body=(
                    "private body"
                ),
                pair_id="pair-private",
                scheduled_value=(
                    "2026-08-20 18:03"
                ),
            )

        error = raised.exception

        self.assertEqual(
            error.code,
            "auth",
        )

        rendered = "".join(
            traceback.format_exception(
                error
            )
        )

        for private_value in (
            "private-server-response",
            "private-app-password",
            "private reminder",
            "private body",
        ):
            self.assertNotIn(
                private_value,
                rendered,
            )

    def test_default_subject_uses_saved_language(
        self,
    ):
        self.save_gmail()

        settings = (
            runtime_config
            .load_settings()
        )
        settings["language"] = "es"
        runtime_config.save_settings(
            settings
        )

        message = (
            smtp_transport
            .build_message(
                config=(
                    smtp_transport
                    .load_config()
                ),
                subject="",
                body="Body",
                pair_id="pair-es",
                scheduled_value=(
                    "2026-08-20 18:04"
                ),
            )
        )

        self.assertEqual(
            message["Subject"],
            "Recordatorio",
        )


if __name__ == "__main__":
    unittest.main()
