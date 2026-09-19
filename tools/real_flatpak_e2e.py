#!/usr/bin/env python3
"""One-shot, owner-only SMTP + Notification Portal release proof.

This source-only QA utility is intentionally not installed with the app.  Run
it through the final Flatpak's Python interpreter on stdin.  It refuses to run
outside Flatpak, never prints an address or credential, and places reminder,
history, cache, and log data in a temporary sandbox directory.  The existing
configured profile is read-only for the duration of the proof.
"""

from __future__ import annotations

import argparse
import configparser
import datetime as dt
import hashlib
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


EXIT_TRUE_FAILURE = 41
APP_ID = "io.github.dasguardcorenotify_del.hatirlatici"
APP_VERSION = "2.0.0"
INSTALLED_ROOT = Path("/app/lib/hatirlatici")


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, str], ...]:
    result = []
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            fingerprint = "symlink:" + os.readlink(path)
        elif stat.S_ISDIR(metadata.st_mode):
            fingerprint = "directory"
        elif stat.S_ISREG(metadata.st_mode):
            fingerprint = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            fingerprint = "special"
        result.append(
            (
                path.relative_to(root).as_posix(),
                mode,
                fingerprint,
            )
        )
    return tuple(result)


def _make_due(core, path: Path, pair_id: str, due: dt.datetime) -> None:
    fields, rows = core.read_csv(path, core.FIELDS)
    found = False
    for row in rows:
        if str(row.get("pair_id", "")).strip() != pair_id:
            continue
        row["next_run"] = core.fmt_dt(due)
        row["lease_until"] = ""
        row["snooze_until"] = ""
        found = True
    if not found:
        raise RuntimeError("isolated occurrence was not created")
    core.atomic_write(path, core.ensure_fields(fields), rows)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _attest_flatpak() -> None:
    info = configparser.ConfigParser(interpolation=None)
    if not info.read("/.flatpak-info", encoding="utf-8"):
        raise RuntimeError("Flatpak identity metadata is unavailable")
    if info.get("Application", "name", fallback="") != APP_ID:
        raise RuntimeError("unexpected Flatpak application identity")
    runtime = info.get("Application", "runtime", fallback="")
    if not (
        runtime.startswith("org.freedesktop.Platform/")
        and runtime.endswith("/25.08")
    ):
        raise RuntimeError("unexpected Flatpak runtime identity")
    if not (
        (INSTALLED_ROOT / "runtime_config.py").is_file()
        and (INSTALLED_ROOT / "ui_v2" / "core_v2.py").is_file()
        and (INSTALLED_ROOT / "app_identity.py").is_file()
    ):
        raise RuntimeError("installed application code is incomplete")


def _run_isolated(real_config_root: Path, isolated_root: Path) -> int:
    config_home = isolated_root / "config"
    copied_config_root = config_home / "hatirlatici"
    for name in ("config", "data", "state", "cache"):
        directory = isolated_root / name
        directory.mkdir(mode=0o700)
    if any(path.is_symlink() for path in real_config_root.rglob("*")):
        raise RuntimeError("real configuration contains a symbolic link")
    shutil.copytree(
        real_config_root,
        copied_config_root,
        copy_function=shutil.copy2,
    )
    copied_config_root.chmod(0o700)

    os.environ["XDG_CONFIG_HOME"] = str(config_home)
    os.environ["XDG_DATA_HOME"] = str(isolated_root / "data")
    os.environ["XDG_STATE_HOME"] = str(isolated_root / "state")
    os.environ["XDG_CACHE_HOME"] = str(isolated_root / "cache")

    sys.path[:0] = [
        str(INSTALLED_ROOT),
        str(INSTALLED_ROOT / "ui_v2"),
    ]

    import app_identity
    import credential_vault
    import mail_dispatch
    import pc_notify
    import portal_notifications
    import runtime_config
    import smtp_transport
    import core_v2 as core

    if (
        app_identity.APP_ID != APP_ID
        or app_identity.APP_VERSION != APP_VERSION
        or app_identity.FLATPAK_RUNTIME != "org.freedesktop.Platform"
        or app_identity.FLATPAK_RUNTIME_VERSION != "25.08"
    ):
        raise RuntimeError("installed release identity contract mismatch")
    if runtime_config.config_dir().resolve() != copied_config_root.resolve():
        raise RuntimeError("configuration isolation failed")

    settings = runtime_config.load_settings()
    config = smtp_transport.load_config()
    if config.provider != "gmail":
        raise RuntimeError("configured provider is not Gmail")
    if not (
        config.from_email
        and config.from_email == config.to_email
        and config.username == config.from_email
    ):
        raise RuntimeError("configured owner destination mismatch")
    if not settings.get("email_enabled") or not settings.get("email_ready"):
        raise RuntimeError("configured email profile is not ready")

    settings_path = runtime_config.settings_path()
    vault_path = runtime_config.credential_vault_path()
    if _mode(settings_path) != 0o600 or _mode(vault_path) != 0o600:
        raise RuntimeError("profile file mode mismatch")

    runtime_config.ensure_runtime_dirs()
    core.migrate_mail_schema()
    core.ensure_pc_schema()
    core.ensure_history_schema()

    now = dt.datetime.now().replace(second=0, microsecond=0)
    core.save_settings({"quiet_hours_enabled": False})
    pc_settings = core.load_settings()
    if core.is_quiet_time(now, pc_settings):
        raise RuntimeError("isolated PC quiet-hours preflight failed")

    if portal_notifications.portal_version() < 2:
        raise RuntimeError("Notification Portal v2 is unavailable")
    preflight_id = "hatirlatici-e2e-preflight-" + uuid.uuid4().hex[:12]
    submitted = False
    try:
        portal_notifications.add_notification(
            preflight_id,
            "Hatırlatıcı final QA",
            "Notification Portal preflight",
            action_buttons=False,
            language="en",
        )
        submitted = True
    finally:
        if submitted:
            portal_notifications.remove_notification(preflight_id)

    future = now + dt.timedelta(minutes=5)
    due = now - dt.timedelta(minutes=1)
    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    subject = "Hatırlatıcı 2.0.0 final QA"
    body = "Controlled owner-only release verification."
    pair_id = core.save_group(
        pair_id=None,
        channel="both",
        subject=subject,
        body=body,
        run_at=future,
        repeat="once",
        category="Genel",
    )
    with core.exclusive(core.MAIL_LOCK), core.exclusive(core.PC_LOCK):
        _make_due(core, core.MAIL_CSV, pair_id, due)
        _make_due(core, core.PC_CSV, pair_id, due)

    scheduled_value = core.fmt_dt(due)
    message_id = smtp_transport.deterministic_message_id(
        pair_id=pair_id,
        scheduled_value=scheduled_value,
        from_email=config.from_email,
    )
    message_id_digest = hashlib.sha256(
        message_id.encode("utf-8")
    ).hexdigest()

    mail_result = mail_dispatch._dispatch()
    print("REAL_E2E_TIMESTAMP_UTC=" + timestamp.isoformat())
    print("REAL_E2E_DESTINATION=CONFIGURED_OWNER_ONLY")
    print("REAL_E2E_PROVIDER=GMAIL")
    print("MESSAGE_ID_SHA256=" + message_id_digest)
    print("SMTP_STATUS=" + mail_result.status.upper())
    print("SMTP_CODE=" + mail_result.code)
    if mail_result.exit_code != 0 or mail_result.status != "ok":
        print("REAL_SMTP_E2E=FAIL")
        return EXIT_TRUE_FAILURE

    print("CREDENTIAL_DECRYPTABLE=YES")
    print("REAL_SMTP_E2E=PASS")
    print("PC_NOTIFICATION_WAITING_FOR_OPTIONAL_ACTION=YES", flush=True)
    pc_result = pc_notify.run()
    print("PC_DISPATCH_EXIT=" + str(pc_result))

    events = [
        event
        for event in core.load_history()
        if str(event.get("pair_id", "")).strip() == pair_id
    ]
    email_events = [event for event in events if event.get("channel") == "email"]
    pc_events = [event for event in events if event.get("channel") == "pc"]
    pc_action = str(pc_events[0].get("action", "")) if len(pc_events) == 1 else ""
    print("REAL_EMAIL_EVENT_COUNT=" + str(len(email_events)))
    print("REAL_PC_EVENT_COUNT=" + str(len(pc_events)))
    print("REAL_PC_ACTION=" + (pc_action or "NONE"))

    if pc_result != 0 or len(email_events) != 1 or len(pc_events) != 1:
        print("REAL_BOTH_E2E=FAIL")
        return EXIT_TRUE_FAILURE

    print("REAL_BOTH_E2E=PASS")
    return 0


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-real-send-to-configured-owner",
        action="store_true",
        help="authorize exactly one message to the already configured owner address",
    )
    args = parser.parse_args()

    if not args.confirm_real_send_to_configured_owner:
        print("REAL_BOTH_E2E=REFUSED_MISSING_EXPLICIT_CONFIRMATION")
        return EXIT_TRUE_FAILURE
    if not Path("/.flatpak-info").is_file():
        print("REAL_BOTH_E2E=REFUSED_NOT_FLATPAK")
        return EXIT_TRUE_FAILURE

    config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if not config_home:
        print("REAL_BOTH_E2E=FAIL_CONFIG_ROOT_MISSING")
        return EXIT_TRUE_FAILURE

    config_root = Path(config_home) / "hatirlatici"
    if not config_root.is_dir():
        print("REAL_BOTH_E2E=FAIL_CONFIG_MISSING")
        return EXIT_TRUE_FAILURE
    try:
        _attest_flatpak()
        real_snapshot = _tree_snapshot(config_root)
    except Exception as exc:
        print("REAL_E2E_SAFE_FAILURE_TYPE=" + type(exc).__name__)
        print("REAL_SMTP_E2E=FAIL")
        print("REAL_BOTH_E2E=FAIL")
        return EXIT_TRUE_FAILURE

    result_code = EXIT_TRUE_FAILURE
    try:
        with tempfile.TemporaryDirectory(
            prefix="hatirlatici-real-e2e-"
        ) as temp_name:
            result_code = _run_isolated(config_root, Path(temp_name))
    except Exception as exc:
        print("REAL_E2E_SAFE_FAILURE_TYPE=" + type(exc).__name__)
        print("REAL_SMTP_E2E=FAIL")
        print("REAL_BOTH_E2E=FAIL")

    try:
        unchanged = _tree_snapshot(config_root) == real_snapshot
    except Exception:
        unchanged = False
    print("REAL_CONFIG_UNCHANGED=" + ("YES" if unchanged else "NO"))
    return result_code if unchanged else EXIT_TRUE_FAILURE


if __name__ == "__main__":
    raise SystemExit(run())
