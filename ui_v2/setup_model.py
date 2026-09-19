#!/usr/bin/env python3
"""Canonical normalization and validation for first-run settings."""
from __future__ import annotations

import re
from typing import Any

import l10n


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LANGUAGES = frozenset(l10n.SUPPORTED_LANGUAGES)
CHANNELS = frozenset({"pc", "email", "both"})
PROVIDERS = frozenset({"gmail", "custom"})
SECURITY_MODES = frozenset({"starttls", "implicit_tls"})
FORBIDDEN_SECRET_KEYS = frozenset(
    {
        "password",
        "passwd",
        "smtp_password",
        "smtp_pass",
        "secret",
        "token",
        "access_token",
        "api_key",
    }
)


def clean_name(value: object) -> str:
    text = " ".join(str(value or "").split())
    if any(ord(char) < 32 for char in text):
        return ""
    return text[:80]


def valid_email(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text and EMAIL_RE.fullmatch(text))


def contains_secret_keys(payload: dict[str, Any]) -> bool:
    normalized = {
        str(key).lower().replace("-", "_")
        for key in payload
    }
    return bool(normalized & FORBIDDEN_SECRET_KEYS)


def validate_profile(
    payload: dict[str, Any],
    *,
    language: str = "en",
) -> list[str]:
    errors: list[str] = []
    if not clean_name(payload.get("profile_name", "")):
        errors.append(l10n.text("name_required", language))
    if payload.get("language") not in LANGUAGES:
        errors.append(l10n.text("required_title", language))
    return errors


def validate_email(
    payload: dict[str, Any],
    *,
    language: str = "en",
) -> list[str]:
    if not bool(payload.get("email_enabled", False)):
        return []

    errors: list[str] = []
    provider = payload.get("smtp_provider")
    if provider not in PROVIDERS:
        return [l10n.text("custom_required", language)]

    if not valid_email(payload.get("mail_from_email", "")) or not valid_email(
        payload.get("mail_to_email", "")
    ):
        errors.append(l10n.text("email_required", language))

    if provider == "custom":
        host = str(payload.get("smtp_host", "")).strip()
        try:
            port = int(payload.get("smtp_port", 0))
        except (TypeError, ValueError):
            port = 0
        security = str(payload.get("smtp_security", "")).strip().lower()
        if not host or not 1 <= port <= 65535 or security not in SECURITY_MODES:
            errors.append(l10n.text("custom_required", language))

    return errors


def validate_setup(
    payload: dict[str, Any],
    *,
    language: str = "en",
) -> list[str]:
    errors = validate_profile(payload, language=language)

    channel = payload.get("default_channel")
    if channel not in CHANNELS:
        errors.append(l10n.text("required_title", language))

    email_enabled = bool(payload.get("email_enabled", False))
    if channel in {"email", "both"} and not email_enabled:
        errors.append(l10n.text("email_required", language))
    errors.extend(validate_email(payload, language=language))

    if contains_secret_keys(payload):
        errors.append(l10n.text("required_title", language))

    # Preserve order while suppressing repeated broad validation messages.
    return list(dict.fromkeys(errors))


def normalize_setup(raw: dict[str, Any]) -> dict[str, Any]:
    provider = str(raw.get("smtp_provider", "gmail")).strip().lower()
    if provider == "gmail":
        host = "smtp.gmail.com"
        port_raw: object = 587
        security = "starttls"
    else:
        host = str(raw.get("smtp_host", "")).strip()
        port_raw = raw.get("smtp_port", 587)
        security = str(raw.get("smtp_security", "starttls")).strip().lower()

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 0

    return {
        "setup_complete": True,
        "setup_version": 2,
        "profile_name": clean_name(raw.get("profile_name", "")),
        "language": str(raw.get("language", "en")).strip().lower(),
        "default_channel": str(raw.get("default_channel", "pc")).strip().lower(),
        "email_enabled": bool(raw.get("email_enabled", False)),
        "email_ready": False,
        "smtp_provider": provider,
        "smtp_host": host,
        "smtp_port": port,
        "smtp_security": security,
        "smtp_username": str(raw.get("smtp_username", "")).strip(),
        "mail_from_email": str(raw.get("mail_from_email", "")).strip(),
        "mail_to_email": str(raw.get("mail_to_email", "")).strip(),
    }
