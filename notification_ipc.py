#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import BinaryIO


PROTOCOL_VERSION = 1

# Keep the complete anonymous-pipe write comfortably below common Linux
# pipe capacities.  Desktop notification services also benefit from a
# bounded title/body instead of accepting an unbounded CSV field.
MAX_PAYLOAD_BYTES = 24 * 1024
MAX_TITLE_CHARS = 200
MAX_BODY_CHARS = 4096


class NotificationPayloadError(
    ValueError
):
    pass


def _clean_text(
    value: object,
    *,
    limit: int,
    one_line: bool = False,
) -> str:
    text = str(
        value or ""
    ).replace(
        "\x00",
        "\N{REPLACEMENT CHARACTER}",
    )

    if one_line:
        text = " ".join(
            text.replace(
                "\r",
                " ",
            ).replace(
                "\n",
                " ",
            ).split()
        )

    return text[:limit]


def encode_payload(
    subject: object,
    body: object,
    *,
    token: object,
    default_title: object = "Reminder",
) -> bytes:
    clean_default = (
        _clean_text(
            default_title,
            limit=MAX_TITLE_CHARS,
            one_line=True,
        )
        or "Reminder"
    )

    title = (
        _clean_text(
            subject,
            limit=MAX_TITLE_CHARS,
            one_line=True,
        )
        or clean_default
    )

    clean_body = _clean_text(
        body,
        limit=MAX_BODY_CHARS,
    )

    if not clean_body:
        clean_body = title

    clean_token = str(
        token or ""
    ).strip()

    if (
        not clean_token
        or len(clean_token) > 64
        or not all(
            character.isascii()
            and (
                character.isalnum()
                or character in "-_"
            )
            for character in clean_token
        )
    ):
        raise NotificationPayloadError(
            "notification token is invalid"
        )

    payload = json.dumps(
        {
            "version":
                PROTOCOL_VERSION,

            "subject":
                title,

            "body":
                clean_body,

            "token":
                clean_token,
        },
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    if len(payload) > MAX_PAYLOAD_BYTES:
        # The character limits above make this unreachable for valid
        # Unicode, but retain a fail-closed byte boundary as part of the
        # IPC contract.
        raise NotificationPayloadError(
            "notification payload is too large"
        )

    return payload


def decode_payload(
    payload: bytes,
) -> tuple[str, str, str]:
    if not payload:
        raise NotificationPayloadError(
            "notification payload is empty"
        )

    if len(payload) > MAX_PAYLOAD_BYTES:
        raise NotificationPayloadError(
            "notification payload is too large"
        )

    try:
        value = json.loads(
            payload.decode(
                "utf-8",
                errors="strict",
            )
        )
    except (
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise NotificationPayloadError(
            "notification payload is invalid"
        ) from exc

    if (
        not isinstance(value, dict)
        or value.get("version")
        != PROTOCOL_VERSION
        or set(value)
        != {
            "version",
            "subject",
            "body",
            "token",
        }
    ):
        raise NotificationPayloadError(
            "notification payload schema is invalid"
        )

    subject = value.get(
        "subject"
    )
    body = value.get(
        "body"
    )
    token = value.get(
        "token"
    )

    if (
        not isinstance(subject, str)
        or not isinstance(body, str)
        or not isinstance(token, str)
        or not subject
        or not token
        or len(subject) > MAX_TITLE_CHARS
        or len(body) > MAX_BODY_CHARS
        or len(token) > 64
        or "\x00" in subject
        or "\x00" in body
        or not all(
            character.isascii()
            and (
                character.isalnum()
                or character in "-_"
            )
            for character in token
        )
    ):
        raise NotificationPayloadError(
            "notification payload fields are invalid"
        )

    return subject, body, token


def read_payload(
    stream: BinaryIO,
) -> tuple[str, str, str]:
    # Read one byte beyond the contract limit so oversized or unclosed
    # senders are rejected without allocating unbounded memory.
    payload = stream.read(
        MAX_PAYLOAD_BYTES + 1
    )

    return decode_payload(
        payload
    )
