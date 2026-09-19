#!/usr/bin/env python3
from __future__ import annotations

import os
import select
import secrets
import sys
import time
from dataclasses import dataclass
from typing import Any


SERVICE = "org.freedesktop.portal.Desktop"

OBJECT_PATH = (
    "/org/freedesktop/portal/desktop"
)

INTERFACE = (
    "org.freedesktop.portal.Secret"
)

PROPERTIES_INTERFACE = (
    "org.freedesktop.DBus.Properties"
)

REQUEST_INTERFACE = (
    "org.freedesktop.portal.Request"
)


class SecretPortalError(
    RuntimeError
):
    pass


class SecretPortalUnavailable(
    SecretPortalError
):
    pass


class SecretPortalRequiresFlatpak(
    SecretPortalError
):
    pass


@dataclass(
    frozen=True
)
class SecretResult:
    secret: bytes
    token: str | None
    response: int
    handle: str


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
        raise SecretPortalUnavailable(
            "Gio/GLib D-Bus desteği kullanılamıyor."
        ) from exc

    return Gio, GLib


def _connection():
    Gio, _ = _load_gio()

    try:
        connection = Gio.bus_get_sync(
            Gio.BusType.SESSION,
            None,
        )

    except Exception as exc:
        raise SecretPortalUnavailable(
            "Kullanıcı D-Bus oturumuna bağlanılamadı."
        ) from exc

    if connection is None:
        raise SecretPortalUnavailable(
            "D-Bus bağlantısı yok."
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

    reply = _connection().call_sync(
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

    value = reply.unpack()[0]

    return int(
        _unpack(value)
    )


def new_handle_token() -> str:
    return (
        "hatirlatici_secret_"
        + secrets.token_hex(12)
    )


def build_options(
    *,
    handle_token: str,
    previous_token: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "handle_token":
            str(handle_token),
    }

    if previous_token:
        result["token"] = str(
            previous_token
        )

    return result


def _expected_request_path(
    connection,
    token: str,
) -> str:
    unique_name = (
        connection.get_unique_name()
    )

    if not unique_name:
        raise SecretPortalUnavailable(
            "D-Bus unique name alınamadı."
        )

    sender = (
        unique_name
        .lstrip(":")
        .replace(".", "_")
    )

    return (
        "/org/freedesktop/portal/"
        "desktop/request/"
        + sender
        + "/"
        + token
    )


def _variant_options(
    options: dict[str, Any],
):
    _, GLib = _load_gio()

    return {
        key: GLib.Variant(
            "s",
            str(value),
        )
        for key, value
        in options.items()
    }


def _read_secret_fd(
    fd: int,
    *,
    timeout_seconds: float = 3.0,
) -> bytes:
    os.set_blocking(
        fd,
        False,
    )

    deadline = (
        time.monotonic()
        + max(
            0.5,
            float(
                timeout_seconds
            ),
        )
    )

    chunks: list[bytes] = []

    while (
        time.monotonic()
        < deadline
    ):
        remaining = max(
            0.0,
            deadline
            - time.monotonic(),
        )

        readable, _, _ = (
            select.select(
                [fd],
                [],
                [],
                min(
                    remaining,
                    0.25,
                ),
            )
        )

        if not readable:
            if chunks:
                break

            continue

        try:
            chunk = os.read(
                fd,
                65536,
            )

        except BlockingIOError:
            continue

        if not chunk:
            break

        chunks.append(
            chunk
        )

        if sum(
            len(item)
            for item in chunks
        ) > 1024 * 1024:
            raise SecretPortalError(
                "Portal secret beklenenden büyük."
            )

    secret = b"".join(
        chunks
    )

    if not secret:
        raise SecretPortalError(
            "Secret Portal boş secret döndürdü."
        )

    return secret


def retrieve_secret(
    *,
    previous_token: str | None = None,
    timeout_seconds: float = 30.0,
    require_flatpak: bool = True,
) -> SecretResult:
    if (
        require_flatpak
        and not is_flatpak()
    ):
        raise SecretPortalRequiresFlatpak(
            "Gerçek uygulama secret'ı yalnız "
            "kurulu Flatpak içinden alınmalıdır."
        )

    if portal_version() < 1:
        raise SecretPortalUnavailable(
            "Secret Portal v1 gerekli."
        )

    Gio, GLib = _load_gio()

    connection = _connection()

    handle_token = (
        new_handle_token()
    )

    expected_handle = (
        _expected_request_path(
            connection,
            handle_token,
        )
    )

    response_state: dict[
        str,
        Any,
    ] = {
        "response": None,
        "token": None,
    }

    loop = GLib.MainLoop()

    def response_callback(
        _connection,
        _sender,
        _object_path,
        _interface,
        _signal,
        parameters,
        _user_data,
    ):
        try:
            response, results = (
                parameters.unpack()
            )

            response_state[
                "response"
            ] = int(response)

            if isinstance(
                results,
                dict,
            ):
                token_value = (
                    results.get(
                        "token"
                    )
                )

                if token_value is not None:
                    response_state[
                        "token"
                    ] = str(
                        _unpack(
                            token_value
                        )
                    )

        finally:
            if loop.is_running():
                loop.quit()

    subscription = (
        connection.signal_subscribe(
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

    read_fd, write_fd = (
        os.pipe()
    )

    fd_list = (
        Gio.UnixFDList.new()
    )

    handle_index = (
        fd_list.append(
            write_fd
        )
    )

    options = build_options(
        handle_token=handle_token,
        previous_token=previous_token,
    )

    timed_out = {
        "value": False,
    }

    def timeout_callback():
        timed_out[
            "value"
        ] = True

        if loop.is_running():
            loop.quit()

        return GLib.SOURCE_REMOVE

    timeout_source = GLib.timeout_add(
        max(
            1000,
            int(
                timeout_seconds
                * 1000
            ),
        ),
        timeout_callback,
    )

    returned_handle = (
        expected_handle
    )

    try:
        result = (
            connection
            .call_with_unix_fd_list_sync(
                SERVICE,
                OBJECT_PATH,
                INTERFACE,
                "RetrieveSecret",
                GLib.Variant(
                    "(ha{sv})",
                    (
                        handle_index,
                        _variant_options(
                            options
                        ),
                    ),
                ),
                None,
                Gio.DBusCallFlags.NONE,
                5000,
                fd_list,
                None,
            )
        )

        if isinstance(
            result,
            tuple,
        ):
            reply = result[0]
        else:
            reply = result

        returned_handle = str(
            reply.unpack()[0]
        )

        # Local write end must close.
        # The portal has its duplicated descriptor.
        os.close(
            write_fd
        )

        write_fd = -1

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
                connection.signal_subscribe(
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

            raise SecretPortalError(
                "Secret Portal isteği zaman aşımına uğradı."
            )

        response = (
            response_state[
                "response"
            ]
        )

        if response is None:
            raise SecretPortalError(
                "Secret Portal Response üretmedi."
            )

        if int(response) != 0:
            raise SecretPortalError(
                "Secret Portal isteği tamamlanmadı. "
                f"response={response}"
            )

        secret = _read_secret_fd(
            read_fd
        )

        return SecretResult(
            secret=secret,
            token=(
                response_state[
                    "token"
                ]
            ),
            response=int(
                response
            ),
            handle=returned_handle,
        )

    except SecretPortalError:
        raise

    except Exception as exc:
        raise SecretPortalError(
            "Secret Portal RetrieveSecret çağrısı başarısız."
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

        if write_fd >= 0:
            try:
                os.close(
                    write_fd
                )
            except OSError:
                pass

        try:
            os.close(
                read_fd
            )
        except OSError:
            pass


def selftest() -> int:
    version = portal_version()

    print(
        "SECRET_PORTAL_VERSION="
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
        handle_token=(
            "hatirlatici_secret_selftest"
        ),
        previous_token=(
            "opaque_previous_token"
        ),
    )

    assert (
        options[
            "handle_token"
        ]
        == "hatirlatici_secret_selftest"
    )

    assert (
        options[
            "token"
        ]
        == "opaque_previous_token"
    )

    print(
        "SECRET_PORTAL_OPTIONS_MODEL=PASS"
    )

    print(
        "SECRET_PORTAL_RETRIEVE=DEFERRED_TO_TEST_FLATPAK"
    )

    print(
        "SECRET_PORTAL_SELFTEST=PASS"
    )

    return 0


def main() -> int:
    if (
        "--selftest"
        in sys.argv[1:]
    ):
        return selftest()

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
