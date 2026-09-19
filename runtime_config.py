#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


APP_SLUG = "hatirlatici"


def _xdg_dir(
    env_name: str,
    fallback: Path,
) -> Path:
    raw = os.environ.get(
        env_name,
        "",
    ).strip()

    if raw:
        return Path(raw).expanduser()

    return fallback


def config_dir() -> Path:
    base = _xdg_dir(
        "XDG_CONFIG_HOME",
        Path.home() / ".config",
    )

    return base / APP_SLUG


def data_dir() -> Path:
    base = _xdg_dir(
        "XDG_DATA_HOME",
        Path.home()
        / ".local"
        / "share",
    )

    return base / APP_SLUG


def state_dir() -> Path:
    base = _xdg_dir(
        "XDG_STATE_HOME",
        Path.home()
        / ".local"
        / "state",
    )

    return base / APP_SLUG


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    path = settings_path()

    if not path.exists():
        return {}

    try:
        raw = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(raw, dict):
        return {}

    return raw


def save_settings(
    settings: dict[str, Any],
) -> None:
    path = settings_path()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    payload = json.dumps(
        settings,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=".settings.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(payload)
            handle.write("\n")
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

    finally:
        try:
            os.unlink(
                temp_name
            )
        except FileNotFoundError:
            pass


def get_text(
    key: str,
    default: str = "",
) -> str:
    value = load_settings().get(
        key,
        default,
    )

    if value is None:
        return default

    return str(value).strip()


def profile_name() -> str:
    return (
        get_text(
            "profile_name",
            "Kullanıcı",
        )
        or "Kullanıcı"
    )
# HATIRLATICI_XDG_RUNTIME_CONTRACT_V1

def code_root() -> Path:
    """Installed/read-only application source root."""
    return (
        Path(__file__)
        .resolve()
        .parent
    )


def mail_csv_path() -> Path:
    return (
        data_dir()
        / "hatirlatmalar.csv"
    )


def pc_csv_path() -> Path:
    return (
        data_dir()
        / "pc_hatirlatmalar.csv"
    )


def history_path() -> Path:
    return (
        state_dir()
        / "hatirlatici_history.csv"
    )


def app_settings_path() -> Path:
    return (
        config_dir()
        / "settings_v2.json"
    )


def data_backups_dir() -> Path:
    return (
        state_dir()
        / "data_backups"
    )


def logs_dir() -> Path:
    return (
        state_dir()
        / "logs"
    )


def locks_dir() -> Path:
    return (
        state_dir()
        / "locks"
    )


def mail_lock_path() -> Path:
    return (
        locks_dir()
        / "hatirlatmalar.lock"
    )


def pc_lock_path() -> Path:
    return (
        locks_dir()
        / "pc_hatirlatmalar.lock"
    )


def history_lock_path() -> Path:
    return (
        locks_dir()
        / "hatirlatici_history.lock"
    )


def legacy_dir() -> Path:
    return (
        state_dir()
        / "legacy"
    )


def ensure_runtime_dirs() -> None:
    for directory in (
        config_dir(),
        data_dir(),
        state_dir(),
        data_backups_dir(),
        logs_dir(),
        locks_dir(),
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )


def _cli() -> int:
    import sys

    args = set(
        sys.argv[1:]
    )

    if "--ensure" in args:
        ensure_runtime_dirs()
        print(
            "RUNTIME_DIRS_READY=YES"
        )
        return 0

    mapping = {
        "--code-root":
            code_root(),

        "--config-dir":
            config_dir(),

        "--data-dir":
            data_dir(),

        "--state-dir":
            state_dir(),

        "--mail-csv":
            mail_csv_path(),

        "--pc-csv":
            pc_csv_path(),

        "--history":
            history_path(),
    }

    for option, value in mapping.items():
        if option in args:
            print(value)
            return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(
        _cli()
    )

# HATIRLATICI_CREDENTIAL_VAULT_PATHS_V1

def credential_vault_path() -> Path:
    return (
        config_dir()
        / "credentials.v1.json"
    )


def secret_portal_state_path() -> Path:
    return (
        config_dir()
        / "secret-portal.v1.json"
    )
