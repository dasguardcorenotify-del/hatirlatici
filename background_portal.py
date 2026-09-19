#!/usr/bin/env python3
from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass
from typing import Any


SERVICE = (
    "org.freedesktop.portal.Desktop"
)

OBJECT_PATH = (
    "/org/freedesktop/portal/desktop"
)

INTERFACE = (
    "org.freedesktop.portal.Background"
)

PROPERTIES_INTERFACE = (
    "org.freedesktop.DBus.Properties"
)

REQUEST_INTERFACE = (
    "org.freedesktop.portal.Request"
)


class BackgroundPortalError(
    RuntimeError
):
    pass


class BackgroundPortalUnavailable(
    BackgroundPortalError
):
    pass


class BackgroundPortalRequiresFlatpak(
    BackgroundPortalError
):
    pass


@dataclass(
    frozen=True
)
class BackgroundResult:
    response: int
    background: bool
    autostart: bool
    handle: str

    @property
    def success(self) -> bool:
        return (
            self.response == 0
        )


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
        raise (
            BackgroundPortalUnavailable(
                "Gio/GLib D-Bus desteği kullanılamıyor."
            )
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
        raise (
            BackgroundPortalUnavailable(
                "Kullanıcı D-Bus oturumuna bağlanılamadı."
            )
        ) from exc

    if connection is None:
        raise (
            BackgroundPortalUnavailable(
                "Kullanıcı D-Bus bağlantısı yok."
            )
        )

    return connection


def _unpack(
    value: Any,
) -> Any:
    while hasattr(
        value,
        "unpack",
    ):
        value = value.unpack()

    return value


def is_flatpak() -> bool:
    return bool(
        os.environ.get(
            "FLATPAK_ID",
            "",
        ).strip()
        or os.path.isfile(
            "/.flatpak-info"
        )
    )


def portal_version() -> int:
    Gio, GLib = _load_gio()

    connection = _connection()

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

    value = (
        reply.unpack()[0]
    )

    return int(
        _unpack(value)
    )


def new_handle_token() -> str:
    return (
        "hatirlatici_"
        + secrets.token_hex(12)
    )


def build_options(
    *,
    reason: str,
    autostart: bool,
    handle_token: str,
    commandline: list[str] | None = None,
) -> dict[str, Any]:
    reason = (
        " ".join(
            str(reason).split()
        )[:240]
    )

    result: dict[str, Any] = {
        "handle_token":
            str(handle_token),

        "reason":
            reason,

        "autostart":
            bool(autostart),
    }

    if commandline:
        result[
            "commandline"
        ] = [
            str(item)
            for item in commandline
        ]

    return result


def _options_variant(
    options: dict[str, Any],
):
    _, GLib = _load_gio()

    payload = {}

    for key, value in (
        options.items()
    ):
        if isinstance(
            value,
            bool,
        ):
            payload[key] = (
                GLib.Variant(
                    "b",
                    value,
                )
            )

        elif isinstance(
            value,
            list,
        ):
            payload[key] = (
                GLib.Variant(
                    "as",
                    [
                        str(item)
                        for item
                        in value
                    ],
                )
            )

        else:
            payload[key] = (
                GLib.Variant(
                    "s",
                    str(value),
                )
            )

    return payload


def _expected_request_path(
    connection,
    token: str,
) -> str:
    unique_name = (
        connection
        .get_unique_name()
    )

    if not unique_name:
        raise (
            BackgroundPortalUnavailable(
                "D-Bus unique name alınamadı."
            )
        )

    sender = (
        unique_name
        .lstrip(":")
        .replace(
            ".",
            "_",
        )
    )

    return (
        "/org/freedesktop/portal/"
        "desktop/request/"
        + sender
        + "/"
        + token
    )


def request_background(
    *,
    reason: str,
    autostart: bool = True,
    parent_window: str = "",
    timeout_seconds: float = 60.0,
    require_flatpak: bool = True,
) -> BackgroundResult:
    if (
        require_flatpak
        and not is_flatpak()
    ):
        raise (
            BackgroundPortalRequiresFlatpak(
                "Gerçek Background Portal izni "
                "kurulu Flatpak içinden istenmelidir."
            )
        )

    if portal_version() < 2:
        raise (
            BackgroundPortalUnavailable(
                "Background Portal v2 gerekli."
            )
        )

    Gio, GLib = _load_gio()

    connection = _connection()

    token = (
        new_handle_token()
    )

    expected_handle = (
        _expected_request_path(
            connection,
            token,
        )
    )

    options = build_options(
        reason=reason,
        autostart=autostart,
        handle_token=token,
        # commandline bilerek verilmez.
        # Portal desktop dosyasındaki Exec'i kullanır.
        commandline=None,
    )

    result = {
        "response": None,
        "background": False,
        "autostart": False,
    }

    loop = GLib.MainLoop()

    def response_callback(
        _connection,
        _sender_name,
        _object_path,
        _interface_name,
        _signal_name,
        parameters,
        _user_data,
    ):
        try:
            response, values = (
                parameters.unpack()
            )

            result[
                "response"
            ] = int(response)

            if isinstance(
                values,
                dict,
            ):
                result[
                    "background"
                ] = bool(
                    _unpack(
                        values.get(
                            "background",
                            False,
                        )
                    )
                )

                result[
                    "autostart"
                ] = bool(
                    _unpack(
                        values.get(
                            "autostart",
                            False,
                        )
                    )
                )

        finally:
            if loop.is_running():
                loop.quit()

    subscription = (
        connection
        .signal_subscribe(
            SERVICE,
            REQUEST_INTERFACE,
            "Response",
            expected_handle,
            None,
            Gio.DBusSignalFlags.NONE,
            response_callback,
            None,
        )
    )

    returned_handle = (
        expected_handle
    )

    timed_out = {
        "value": False,
    }

    timeout_ms = max(
        1000,
        int(
            timeout_seconds
            * 1000
        ),
    )

    def timeout_callback():
        timed_out[
            "value"
        ] = True

        if loop.is_running():
            loop.quit()

        return (
            GLib.SOURCE_REMOVE
        )

    timeout_source = (
        GLib.timeout_add(
            timeout_ms,
            timeout_callback,
        )
    )

    try:
        reply = (
            connection.call_sync(
                SERVICE,
                OBJECT_PATH,
                INTERFACE,
                "RequestBackground",
                GLib.Variant(
                    "(sa{sv})",
                    (
                        str(
                            parent_window
                        ),
                        _options_variant(
                            options
                        ),
                    ),
                ),
                None,
                Gio.DBusCallFlags.NONE,
                5000,
                None,
            )
        )

        returned_handle = str(
            reply.unpack()[0]
        )

        if (
            returned_handle
            != expected_handle
        ):
            try:
                connection.signal_unsubscribe(
                    subscription
                )
            except Exception:
                pass

            subscription = (
                connection
                .signal_subscribe(
                    SERVICE,
                    REQUEST_INTERFACE,
                    "Response",
                    returned_handle,
                    None,
                    Gio.DBusSignalFlags.NONE,
                    response_callback,
                    None,
                )
            )

        loop.run()

    except Exception as exc:
        raise (
            BackgroundPortalError(
                "Background Portal isteği başarısız."
            )
        ) from exc

    finally:
        try:
            connection.signal_unsubscribe(
                subscription
            )
        except Exception:
            pass

        try:
            GLib.source_remove(
                timeout_source
            )
        except Exception:
            pass

    if timed_out[
        "value"
    ]:
        try:
            connection.call_sync(
                SERVICE,
                returned_handle,
                REQUEST_INTERFACE,
                "Close",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                3000,
                None,
            )
        except Exception:
            pass

        raise (
            BackgroundPortalError(
                "Background Portal isteği zaman aşımına uğradı."
            )
        )

    response = result[
        "response"
    ]

    if response is None:
        raise (
            BackgroundPortalError(
                "Background Portal sonuç üretmedi."
            )
        )

    return BackgroundResult(
        response=int(
            response
        ),
        background=bool(
            result[
                "background"
            ]
        ),
        autostart=bool(
            result[
                "autostart"
            ]
        ),
        handle=returned_handle,
    )


def set_status(
    message: str,
) -> bool:
    if not is_flatpak():
        return False

    if portal_version() < 2:
        return False

    Gio, GLib = _load_gio()

    connection = _connection()

    clean = (
        " ".join(
            str(message).split()
        )[:95]
    )

    try:
        connection.call_sync(
            SERVICE,
            OBJECT_PATH,
            INTERFACE,
            "SetStatus",
            GLib.Variant(
                "(a{sv})",
                (
                    {
                        "message":
                            GLib.Variant(
                                "s",
                                clean,
                            ),
                    },
                ),
            ),
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )

    except Exception:
        return False

    return True


def selftest() -> int:
    version = (
        portal_version()
    )

    print(
        "BACKGROUND_PORTAL_VERSION="
        + str(version)
    )

    print(
        "RUNNING_INSIDE_FLATPAK="
        + (
            "YES"
            if is_flatpak()
            else "NO"
        )
    )

    options = build_options(
        reason=(
            "Hatırlatmaların zamanında "
            "çalışması için."
        ),
        autostart=True,
        handle_token=(
            "hatirlatici_selftest"
        ),
    )

    assert (
        options[
            "autostart"
        ] is True
    )

    assert (
        options[
            "handle_token"
        ]
        == "hatirlatici_selftest"
    )

    print(
        "BACKGROUND_OPTIONS_MODEL=PASS"
    )

    print(
        "BACKGROUND_PERMISSION_PROMPT=NOT_REQUESTED"
    )

    print(
        "BACKGROUND_PORTAL_SELFTEST=PASS"
    )

    return 0


def main() -> int:
    if (
        "--selftest"
        in sys.argv[1:]
    ):
        return selftest()

    print(
        "usage: "
        "background_portal.py --selftest"
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
