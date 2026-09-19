#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from typing import Any


import l10n
import runtime_config


SERVICE = (
    "org.freedesktop.portal.Desktop"
)

OBJECT_PATH = (
    "/org/freedesktop/portal/desktop"
)

INTERFACE = (
    "org.freedesktop.portal.Notification"
)

PROPERTIES_INTERFACE = (
    "org.freedesktop.DBus.Properties"
)

ACTION_COMPLETE = "complete"
ACTION_SNOOZE = "snooze"

KNOWN_ACTIONS = {
    ACTION_COMPLETE,
    ACTION_SNOOZE,
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


class PortalNotificationError(
    RuntimeError
):
    pass


class PortalUnavailable(
    PortalNotificationError
):
    pass


def _load_gio():
    try:
        import gi

        gi.require_version(
            "Gio",
            "2.0",
        )

        from gi.repository import (
            Gio,
            GLib,
        )

    except Exception as exc:
        raise PortalUnavailable(
            "Gio/GLib D-Bus desteği kullanılamıyor."
        ) from exc

    return Gio, GLib


def _connection():
    Gio, _ = _load_gio()

    try:
        connection = (
            Gio.bus_get_sync(
                Gio.BusType.SESSION,
                None,
            )
        )

    except Exception as exc:
        raise PortalUnavailable(
            "Kullanıcı D-Bus oturumuna bağlanılamadı."
        ) from exc

    if connection is None:
        raise PortalUnavailable(
            "Kullanıcı D-Bus bağlantısı yok."
        )

    return connection


def sanitize_id(
    value: str,
) -> str:
    value = str(value)

    cleaned = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "-",
        value,
    ).strip("-")

    if not cleaned:
        cleaned = (
            "hatirlatici-notification"
        )

    return cleaned[:180]


def build_spec(
    title: str,
    body: str,
    *,
    action_buttons: bool = True,
    language: str | None = None,
    snooze_minutes: int = 10,
) -> dict[str, Any]:
    selected_language = (
        l10n.normalize_language(
            language
        )
        if language is not None
        else _current_language()
    )

    try:
        snooze_minutes = int(
            snooze_minutes
        )
    except (
        TypeError,
        ValueError,
    ):
        snooze_minutes = 10

    snooze_minutes = max(
        1,
        min(
            snooze_minutes,
            1440,
        ),
    )

    spec: dict[str, Any] = {
        "title": str(title),
        "body": str(body),
        "priority": "normal",
        "category": "alarm.ringing",
    }

    if action_buttons:
        spec["buttons"] = [
            {
                "label":
                    l10n.text(
                        "notification_complete",
                        selected_language,
                    ),

                "action":
                    ACTION_COMPLETE,
            },
            {
                "label":
                    l10n.text(
                        "notification_snooze_minutes",
                        selected_language,
                        minutes=snooze_minutes,
                    ),

                "action":
                    ACTION_SNOOZE,
            },
        ]

    return spec


def _to_portal_vardict(
    spec: dict[str, Any],
):
    _, GLib = _load_gio()

    payload = {
        "title":
            GLib.Variant(
                "s",
                str(
                    spec.get(
                        "title",
                        "",
                    )
                ),
            ),

        "body":
            GLib.Variant(
                "s",
                str(
                    spec.get(
                        "body",
                        "",
                    )
                ),
            ),

        "priority":
            GLib.Variant(
                "s",
                str(
                    spec.get(
                        "priority",
                        "normal",
                    )
                ),
            ),

        "category":
            GLib.Variant(
                "s",
                str(
                    spec.get(
                        "category",
                        "alarm.ringing",
                    )
                ),
            ),
    }

    buttons = spec.get(
        "buttons",
        [],
    )

    if buttons:
        serialized = []

        for button in buttons:
            serialized.append(
                {
                    "label":
                        GLib.Variant(
                            "s",
                            str(
                                button[
                                    "label"
                                ]
                            ),
                        ),

                    "action":
                        GLib.Variant(
                            "s",
                            str(
                                button[
                                    "action"
                                ]
                            ),
                        ),
                }
            )

        payload["buttons"] = (
            GLib.Variant(
                "aa{sv}",
                serialized,
            )
        )

    return payload


def portal_version() -> int:
    Gio, GLib = _load_gio()

    connection = _connection()

    try:
        reply = connection.call_sync(
            SERVICE,
            OBJECT_PATH,
            PROPERTIES_INTERFACE,
            "Get",
            GLib.Variant(
                "(ss)",
                (
                    INTERFACE,
                    "version",
                ),
            ),
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )

    except Exception as exc:
        raise PortalUnavailable(
            "Notification Portal sürümü okunamadı."
        ) from exc

    value = reply.unpack()[0]

    while hasattr(
        value,
        "unpack",
    ):
        value = value.unpack()

    return int(value)


def add_notification(
    notification_id: str,
    title: str,
    body: str,
    *,
    action_buttons: bool = True,
    language: str | None = None,
    snooze_minutes: int = 10,
    connection=None,
) -> str:
    Gio, GLib = _load_gio()

    if connection is None:
        connection = _connection()

    notification_id = sanitize_id(
        notification_id
    )

    spec = build_spec(
        title,
        body,
        action_buttons=action_buttons,
        language=language,
        snooze_minutes=(
            snooze_minutes
        ),
    )

    payload = _to_portal_vardict(
        spec
    )

    try:
        connection.call_sync(
            SERVICE,
            OBJECT_PATH,
            INTERFACE,
            "AddNotification",
            GLib.Variant(
                "(sa{sv})",
                (
                    notification_id,
                    payload,
                ),
            ),
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )

    except Exception as exc:
        raise PortalNotificationError(
            "Notification Portal bildirimi kabul etmedi."
        ) from exc

    return notification_id


def remove_notification(
    notification_id: str,
    *,
    connection=None,
) -> None:
    Gio, GLib = _load_gio()

    if connection is None:
        connection = _connection()

    notification_id = sanitize_id(
        notification_id
    )

    try:
        connection.call_sync(
            SERVICE,
            OBJECT_PATH,
            INTERFACE,
            "RemoveNotification",
            GLib.Variant(
                "(s)",
                (
                    notification_id,
                ),
            ),
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )

    except Exception as exc:
        raise PortalNotificationError(
            "Portal bildirimi kaldırılamadı."
        ) from exc


def notify_and_wait(
    notification_id: str,
    title: str,
    body: str,
    *,
    timeout_seconds: float = 36.0,
    language: str | None = None,
    snooze_minutes: int = 10,
) -> str | None:
    """
    Submit an actionable notification and wait for one
    portal ActionInvoked signal.

    Returns:
        "complete", "snooze", another action name,
        or None when the bounded wait expires.

    The notification is withdrawn before returning so
    an action can never become stale after this listener
    exits. Background-lifetime activation is migrated in
    the next portal phase.
    """
    Gio, GLib = _load_gio()

    connection = _connection()

    notification_id = sanitize_id(
        notification_id
    )

    result: dict[str, str | None] = {
        "action": None,
    }

    loop = GLib.MainLoop()

    def on_signal(
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
        _user_data,
    ):
        try:
            values = parameters.unpack()

            event_id = str(
                values[0]
            )

            action = str(
                values[1]
            )

        except Exception:
            return

        if event_id != notification_id:
            return

        result["action"] = action

        if loop.is_running():
            loop.quit()

    subscription_id = (
        connection.signal_subscribe(
            SERVICE,
            INTERFACE,
            "ActionInvoked",
            OBJECT_PATH,
            notification_id,
            Gio.DBusSignalFlags.NONE,
            on_signal,
            None,
        )
    )

    timeout_milliseconds = max(
        100,
        int(
            float(
                timeout_seconds
            )
            * 1000
        ),
    )

    def on_timeout():
        if loop.is_running():
            loop.quit()

        return GLib.SOURCE_REMOVE

    timeout_source = (
        GLib.timeout_add(
            timeout_milliseconds,
            on_timeout,
        )
    )

    submitted = False

    try:
        add_notification(
            notification_id,
            title,
            body,
            action_buttons=True,
            language=language,
            snooze_minutes=(
                snooze_minutes
            ),
            connection=connection,
        )

        submitted = True

        loop.run()

    finally:
        try:
            connection.signal_unsubscribe(
                subscription_id
            )
        except Exception:
            pass

        try:
            GLib.source_remove(
                timeout_source
            )
        except Exception:
            pass

        if submitted:
            try:
                remove_notification(
                    notification_id,
                    connection=connection,
                )
            except Exception:
                pass

    return result["action"]


def selftest() -> int:
    version = portal_version()
    language = _current_language()

    print(
        "PORTAL_NOTIFICATION_VERSION="
        + str(version)
    )

    if version < 2:
        print(
            "PORTAL_NOTIFICATION_SELFTEST=FAIL_VERSION"
        )
        return 20

    notification_id = sanitize_id(
        "hatirlatici-selftest-"
        + str(
            os.getpid()
        )
    )

    add_notification(
        notification_id,
        l10n.text(
            "portal_test_title",
            language,
        ),
        l10n.text(
            "portal_test_message",
            language,
        ),
        action_buttons=False,
        language=language,
    )

    remove_notification(
        notification_id
    )

    print(
        "PORTAL_NOTIFICATION_ADD_REMOVE=PASS"
    )

    print(
        "PORTAL_NOTIFICATION_SELFTEST=PASS"
    )

    return 0


def manual_action_test() -> int:
    language = _current_language()

    print(
        "PORTAL_MANUAL_TEST_WAITING=YES",
        flush=True,
    )

    action = notify_and_wait(
        (
            "hatirlatici-manual-"
            + str(
                os.getpid()
            )
        ),
        l10n.text(
            "portal_action_test_title",
            language,
        ),
        l10n.text(
            "portal_action_test_message",
            language,
        ),
        timeout_seconds=30,
        language=language,
    )

    print(
        "PORTAL_MANUAL_ACTION="
        + (
            str(action)
            if action is not None
            else "TIMEOUT"
        )
    )

    if action not in KNOWN_ACTIONS:
        return 30

    print(
        "PORTAL_MANUAL_ACTION_TEST=PASS"
    )

    return 0


def main() -> int:
    args = set(
        sys.argv[1:]
    )

    if "--selftest" in args:
        return selftest()

    if "--manual-action-test" in args:
        return manual_action_test()

    print(
        "usage: portal_notifications.py "
        "--selftest | --manual-action-test"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
