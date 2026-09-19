#!/usr/bin/env python3
from __future__ import annotations

import atexit
import datetime as dt
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui_v2"

sys.path.insert(
    0,
    str(UI),
)

import core_v2 as core  # noqa: E402
import l10n  # noqa: E402
import notification_ipc  # noqa: E402
import runtime_config  # noqa: E402


WORKER = (
    ROOT
    / "notification_action_worker.py"
)

GLOBAL_WORKER_DEADLINE_SECONDS = 44
MAX_JOBS_PER_RUN = 20

WORKER_TERMINATE_GRACE_SECONDS = 0.4
WORKER_KILL_GRACE_SECONDS = 0.4

PC_NOTIFY_OK = 0
PC_NOTIFY_WORKER_FAILURE = 20
PC_NOTIFY_INTERRUPTED = 21

_ACTIVE_WORKERS = []
_SHUTDOWN_REQUESTED = False


def _is_running(
    process,
) -> bool:
    if getattr(
        process,
        "returncode",
        None,
    ) is not None:
        return False

    try:
        return process.poll() is None
    except Exception:
        return True


def _terminate_and_reap(
    processes,
) -> None:
    unique = []
    seen = set()

    for process in processes:
        identity = id(process)

        if identity in seen:
            continue

        seen.add(identity)
        unique.append(process)

    running = [
        process
        for process in unique
        if _is_running(process)
    ]

    for process in running:
        try:
            process.terminate()
        except Exception:
            pass

    deadline = (
        time.monotonic()
        + WORKER_TERMINATE_GRACE_SECONDS
    )

    for process in running:
        if not _is_running(process):
            continue

        try:
            process.wait(
                timeout=max(
                    0.01,
                    deadline
                    - time.monotonic(),
                )
            )
        except Exception:
            pass

    running = [
        process
        for process in running
        if _is_running(process)
    ]

    for process in running:
        try:
            process.kill()
        except Exception:
            pass

    deadline = (
        time.monotonic()
        + WORKER_KILL_GRACE_SECONDS
    )

    for process in running:
        try:
            process.wait(
                timeout=max(
                    0.01,
                    deadline
                    - time.monotonic(),
                )
            )
        except Exception:
            pass


def _cleanup_active_workers() -> None:
    processes = list(
        _ACTIVE_WORKERS
    )

    _terminate_and_reap(
        processes
    )

    _ACTIVE_WORKERS.clear()


def _forget_worker(
    process,
) -> None:
    try:
        _ACTIVE_WORKERS.remove(
            process
        )
    except ValueError:
        pass


def _request_shutdown(
    _signum,
    _frame,
) -> None:
    global _SHUTDOWN_REQUESTED

    _SHUTDOWN_REQUESTED = True

    # Terminate all children concurrently, then apply one global grace
    # period before killing and reaping any holdouts. This completes well
    # inside the Qt scheduler's parent-process shutdown window.
    _cleanup_active_workers()


def _install_signal_handlers():
    previous = {}

    for signum in (
        signal.SIGTERM,
        signal.SIGINT,
    ):
        try:
            previous[signum] = (
                signal.getsignal(
                    signum
                )
            )
            signal.signal(
                signum,
                _request_shutdown,
            )
        except (
            ValueError,
            OSError,
        ):
            pass

    return previous


def _restore_signal_handlers(
    previous,
) -> None:
    for signum, handler in (
        previous.items()
    ):
        try:
            signal.signal(
                signum,
                handler,
            )
        except (
            ValueError,
            OSError,
        ):
            pass


def _spawn_worker(
    argv,
):
    if _SHUTDOWN_REQUESTED:
        raise InterruptedError(
            "notification dispatcher is stopping"
        )

    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

    _ACTIVE_WORKERS.append(
        process
    )

    # A signal can arrive in the very small interval between Popen returning
    # and the child being registered.  The signal handler sets the flag even
    # if it cannot see this child yet, so close that race here.  Do not block
    # signals around Popen: the child would inherit that mask and could not
    # receive the graceful SIGTERM phase.
    if _SHUTDOWN_REQUESTED:
        _terminate_and_reap(
            [
                process,
            ]
        )
        _forget_worker(
            process
        )
        raise InterruptedError(
            "notification dispatcher stopped during worker spawn"
        )

    return process


atexit.register(
    _cleanup_active_workers
)


def _runtime_language() -> str:
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


def release_lease(
    pair_id: str,
    scheduled: str,
    lease_until: str,
) -> None:
    with core.exclusive(
        core.PC_LOCK
    ):
        fields, rows = core.read_csv(
            core.PC_CSV,
            core.FIELDS,
        )

        changed = False

        for row in rows:
            if (
                row.get("pair_id")
                or ""
            ).strip() != pair_id:
                continue

            if (
                row.get("next_run")
                or ""
            ).strip() != scheduled:
                continue

            if (
                row.get("lease_until")
                or ""
            ).strip() != lease_until:
                continue

            row["lease_until"] = ""
            changed = True

        if changed:
            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(fields),
                rows,
            )


def _run_dispatch() -> int:
    now = dt.datetime.now().replace(
        second=0,
        microsecond=0,
    )

    settings = core.load_settings()
    language = _runtime_language()

    default_title = l10n.text(
        "reminder_default_title",
        language,
    )

    if core.is_quiet_time(
        now,
        settings,
    ):
        return 0

    jobs = []

    with core.exclusive(
        core.PC_LOCK
    ):
        fields, rows = core.read_csv(
            core.PC_CSV,
            core.FIELDS,
        )

        fields = core.ensure_fields(
            fields
        )

        changed = False

        for row in rows:
            if len(jobs) >= MAX_JOBS_PER_RUN:
                break

            if (
                row.get("enabled")
                or ""
            ).strip() != "1":
                continue

            scheduled = core.parse_dt(
                row.get(
                    "next_run",
                    "",
                )
            )

            if scheduled is None:
                continue

            if scheduled > now:
                continue

            # Gerçek kullanıcı snooze.
            snooze = core.parse_dt(
                row.get(
                    "snooze_until",
                    "",
                )
            )

            if (
                snooze is not None
                and snooze > now
            ):
                continue

            # Teknik duplicate-delivery lease.
            lease = core.parse_dt(
                row.get(
                    "lease_until",
                    "",
                )
            )

            if (
                lease is not None
                and lease > now
            ):
                continue

            pair_id = (
                row.get("pair_id")
                or f"pc-{row.get('id', '')}"
            )

            lease_until = (
                now
                + dt.timedelta(
                    minutes=2
                )
            )

            lease_value = (
                core.fmt_dt(
                    lease_until
                )
            )

            scheduled_value = (
                row.get("next_run")
                or ""
            ).strip()

            row["lease_until"] = (
                lease_value
            )

            jobs.append(
                {
                    "pair_id": pair_id,
                    "scheduled": (
                        scheduled_value
                    ),
                    "lease": lease_value,
                    "subject": (
                        row.get("subject")
                        or default_title
                    ),
                    "body": (
                        row.get("body")
                        or row.get("subject")
                        or default_title
                    ),
                    "token": (
                        uuid.uuid4()
                        .hex[:12]
                    ),
                }
            )

            changed = True

        if changed:
            core.atomic_write(
                core.PC_CSV,
                fields,
                rows,
            )

    # Tüm worker'lar aynı anda başlatılır.
    # Parent process, ana dispatcher bitmeden
    # worker'ların tamamını bounded şekilde bekler.
    workers = []
    settled_tokens = set()
    failures = 0

    try:
        for job in jobs:
            if _SHUTDOWN_REQUESTED:
                break

            process = None

            try:
                payload = (
                    notification_ipc
                    .encode_payload(
                        job["subject"],
                        job["body"],
                        token=job["token"],
                        default_title=(
                            default_title
                        ),
                    )
                )

                process = _spawn_worker(
                    [
                        sys.executable,
                        str(WORKER),
                        job["pair_id"],
                        job["scheduled"],
                        job["lease"],
                    ]
                )

                if process.stdin is None:
                    raise OSError(
                        "notification worker pipe unavailable"
                    )

                process.stdin.write(
                    payload
                )
                process.stdin.flush()
                process.stdin.close()

                workers.append(
                    (
                        job,
                        process,
                    )
                )

            except Exception:
                failures += 1

                if process is not None:
                    _terminate_and_reap(
                        [
                            process,
                        ]
                    )
                    _forget_worker(
                        process
                    )

                release_lease(
                    job["pair_id"],
                    job["scheduled"],
                    job["lease"],
                )

                settled_tokens.add(
                    job["token"]
                )

        deadline = (
            time.monotonic()
            + GLOBAL_WORKER_DEADLINE_SECONDS
        )

        for job, process in workers:
            if _SHUTDOWN_REQUESTED:
                break

            remaining = max(
                0.1,
                deadline
                - time.monotonic(),
            )

            try:
                returncode = (
                    process.wait(
                        timeout=remaining
                    )
                )

            except subprocess.TimeoutExpired:
                failures += 1

                _terminate_and_reap(
                    [
                        process,
                    ]
                )
                _forget_worker(
                    process
                )

                release_lease(
                    job["pair_id"],
                    job["scheduled"],
                    job["lease"],
                )

                settled_tokens.add(
                    job["token"]
                )

                continue

            _forget_worker(
                process
            )

            if returncode != 0:
                failures += 1

                release_lease(
                    job["pair_id"],
                    job["scheduled"],
                    job["lease"],
                )

            settled_tokens.add(
                job["token"]
            )

    finally:
        _cleanup_active_workers()

        # Any claimed occurrence without a settled worker was interrupted.
        # Release only its exact lease triple; stale/newer state is untouched.
        for job in jobs:
            if job["token"] in settled_tokens:
                continue

            release_lease(
                job["pair_id"],
                job["scheduled"],
                job["lease"],
            )

    if _SHUTDOWN_REQUESTED:
        return PC_NOTIFY_INTERRUPTED

    if failures:
        return PC_NOTIFY_WORKER_FAILURE

    return PC_NOTIFY_OK


def run() -> int:
    global _SHUTDOWN_REQUESTED

    _SHUTDOWN_REQUESTED = False
    previous_handlers = (
        _install_signal_handlers()
    )

    try:
        return _run_dispatch()
    finally:
        _cleanup_active_workers()
        _restore_signal_handlers(
            previous_handlers
        )


if __name__ == "__main__":
    raise SystemExit(run())
