#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

UI = ROOT / "ui_v2"

sys.path.insert(
    0,
    str(ROOT),
)

sys.path.insert(
    0,
    str(UI),
)

import runtime_config
import app_identity


SETUP = (
    UI
    / "first_run_setup.py"
)

APP = (
    UI
    / "hatirlatici_ultimate.py"
)


ONBOARDING_LOCK_NAMESPACE = (
    app_identity.APP_ID
    + ".onboarding"
)


def onboarding_lock_path() -> Path:
    return (
        runtime_config
        .locks_dir()
        / (
            ONBOARDING_LOCK_NAMESPACE
            + ".lock"
        )
    )


def owner_lock_path() -> Path:
    return (
        runtime_config
        .locks_dir()
        / app_identity
        .SINGLE_INSTANCE_OWNER_LOCK
    )


@contextmanager
def try_owner_coordination_lock() -> Iterator[bool]:
    """Hold the main application's lifetime lock during onboarding.

    A forced reconfiguration must never replace an SMTP credential while
    the scheduler is live.  The production window owns this same lock for
    its full lifetime, so a nonblocking failure means setup must fail
    closed instead of racing the running application.
    """
    path = owner_lock_path()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(
            os,
            "O_CLOEXEC",
            0,
        )
        | getattr(
            os,
            "O_NOFOLLOW",
            0,
        )
    )

    fd = os.open(
        path,
        flags,
        0o600,
    )

    try:
        os.fchmod(
            fd,
            0o600,
        )

        try:
            fcntl.flock(
                fd,
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            yield False
            return

        try:
            yield True
        finally:
            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
    finally:
        os.close(fd)


@contextmanager
def try_onboarding_lock() -> Iterator[bool]:
    path = onboarding_lock_path()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(
            os,
            "O_CLOEXEC",
            0,
        )
        | getattr(
            os,
            "O_NOFOLLOW",
            0,
        )
    )

    fd = os.open(
        path,
        flags,
        0o600,
    )

    try:
        os.fchmod(
            fd,
            0o600,
        )

        try:
            fcntl.flock(
                fd,
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            yield False
            return

        try:
            yield True
        finally:
            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
    finally:
        os.close(fd)


def setup_complete() -> bool:
    return bool(
        runtime_config
        .load_settings()
        .get(
            "setup_complete",
            False,
        )
    )


def run_setup() -> int:
    result = subprocess.run(
        [
            sys.executable,
            str(SETUP),
            "--force",
        ],
        check=False,
    )

    return result.returncode


def run_setup_exclusive(
    *,
    force: bool,
) -> tuple[bool, int]:
    with try_owner_coordination_lock() as app_inactive:
        if not app_inactive:
            return False, 12

        with try_onboarding_lock() as acquired:
            if not acquired:
                # Another public launcher owns the only onboarding window.
                # That launcher will continue into the application after a
                # successful setup, so this invocation exits quietly.
                return False, 0

            if (
                not force
                and setup_complete()
            ):
                return True, 0

            return True, run_setup()


def main() -> int:
    args = sys.argv[1:]

    runtime_config.ensure_runtime_dirs()

    if "--selftest" in args:
        print(
            "PUBLIC_LAUNCHER_SELFTEST=PASS"
        )

        print(
            "CONFIG_PATH="
            + str(
                runtime_config
                .settings_path()
            )
        )

        print(
            "SETUP_COMPLETE="
            + (
                "YES"
                if setup_complete()
                else "NO"
            )
        )

        print(
            "ONBOARDING_NAMESPACE="
            + ONBOARDING_LOCK_NAMESPACE
        )

        return 0

    if "--setup-only" in args:
        _, rc = run_setup_exclusive(
            force=True
        )

        return rc

    if not setup_complete():
        acquired, rc = (
            run_setup_exclusive(
                force=False
            )
        )

        if not acquired:
            return 0

        if rc != 0:
            return rc

        if not setup_complete():
            return 11

    # Child application must resolve both root and ui_v2
    # after exec. sys.path mutations do not survive exec.
    path_parts = [
        str(ROOT),
        str(UI),
    ]

    existing_pythonpath = os.environ.get(
        "PYTHONPATH",
        "",
    ).strip()

    if existing_pythonpath:
        path_parts.append(
            existing_pythonpath
        )

    os.environ["PYTHONPATH"] = (
        os.pathsep.join(
            path_parts
        )
    )

    # Yeni process ile gerçek uygulamaya geç:
    # setup QApplication'ı bu noktada yaşamıyor.
    os.execv(
        sys.executable,
        [
            sys.executable,
            str(APP),
            *args,
        ],
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
