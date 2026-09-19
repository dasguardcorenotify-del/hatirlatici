#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import datetime as dt
from pathlib import Path


CODE_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

UI_ROOT = (
    CODE_ROOT
    / "ui_v2"
)

sys.path.insert(
    0,
    str(CODE_ROOT),
)

sys.path.insert(
    0,
    str(UI_ROOT),
)


from PyQt6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QTimer,
    pyqtSignal,
)


import credential_vault
import mail_dispatch
import runtime_config


MAIL_SCRIPT = (
    CODE_ROOT
    / "mail_dispatch.py"
)

MAIL_STATUS_PREFIX = b"MAIL_STATUS_V1 "
MAIL_STATUS_MAX_BYTES = 256

SMTP_ERROR_CODES = frozenset(
    {
        "dns",
        "timeout",
        "tls",
        "auth",
        "invalid_sender",
        "recipient_refused",
        "offline",
        "generic",
    }
)

MAIL_BACKOFF_INITIAL_SECONDS = 60
MAIL_BACKOFF_MAX_SECONDS = 1800


def parse_status_frame(
    payload: bytes,
) -> tuple[str, str] | None:
    if (
        not payload
        or len(payload)
        > MAIL_STATUS_MAX_BYTES
        or not payload.endswith(b"\n")
        or payload.count(b"\n") != 1
        or not payload.startswith(
            MAIL_STATUS_PREFIX
        )
    ):
        return None

    raw = payload[
        len(MAIL_STATUS_PREFIX):-1
    ]

    try:
        value = json.loads(
            raw.decode(
                "ascii",
                errors="strict",
            )
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None

    canonical = json.dumps(
        value,
        ensure_ascii=True,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    ).encode("ascii")

    if raw != canonical:
        return None

    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "code",
            "status",
            "version",
        }
        or value.get("version") != 1
    ):
        return None

    status = value.get("status")
    code = value.get("code")

    if status == "ok" and code == "ok":
        return "ok", "ok"

    if (
        status == "error"
        and isinstance(code, str)
        and code in SMTP_ERROR_CODES
    ):
        return "error", code

    return None


def mail_transport_ready() -> bool:
    settings = (
        runtime_config
        .load_settings()
    )

    return bool(
        settings.get(
            "email_enabled",
            False,
        )
        and settings.get(
            "email_ready",
            False,
        )
        and settings.get(
            "mail_transport_v2_ready",
            False,
        )
        and credential_vault
        .has_smtp_credential()
    )


class MailDeliveryScheduler(
    QObject
):
    statusChanged = pyqtSignal(
        str
    )

    cycleCompleted = pyqtSignal()

    def __init__(
        self,
        *,
        interval_ms: int = 30000,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.interval_ms = max(
            1000,
            int(
                interval_ms
            ),
        )

        self.timer = QTimer(
            self
        )

        self.timer.setInterval(
            self.interval_ms
        )

        self.timer.timeout.connect(
            self.run_cycle
        )

        self.process = QProcess(
            self
        )

        self.process.setProcessChannelMode(
            QProcess.ProcessChannelMode
            .SeparateChannels
        )

        self.process.readyReadStandardOutput.connect(
            self._collect_status_output
        )

        self.process.readyReadStandardError.connect(
            self._discard_stderr
        )

        self.process.finished.connect(
            self._finished
        )

        self.process.errorOccurred.connect(
            self._error
        )

        self._running = False
        self._failure_count = 0
        self._retry_not_before = 0.0
        self._last_error_code = ""
        self._status_buffer = bytearray()
        self._status_overflow = False
        self._cycle_failure_recorded = False

    def _environment(
        self,
    ) -> QProcessEnvironment:
        environment = (
            QProcessEnvironment
            .systemEnvironment()
        )

        paths = [
            str(
                CODE_ROOT
            ),
            str(
                UI_ROOT
            ),
        ]

        existing = (
            environment.value(
                "PYTHONPATH"
            )
        ).strip()

        if existing:
            paths.append(
                existing
            )

        environment.insert(
            "PYTHONPATH",
            os.pathsep.join(
                paths
            ),
        )

        return environment

    def start(
        self,
    ) -> None:
        if self._running:
            return

        runtime_config.ensure_runtime_dirs()

        self._running = True

        self.timer.start()

        self.statusChanged.emit(
            "running"
        )

        QTimer.singleShot(
            350,
            self.run_cycle,
        )

    def stop(
        self,
    ) -> None:
        self._running = False

        self.timer.stop()

        if (
            self.process.state()
            != QProcess.ProcessState
            .NotRunning
        ):
            self.process.terminate()

            if not (
                self.process
                .waitForFinished(
                    1500
                )
            ):
                self.process.kill()

                self.process.waitForFinished(
                    1000
                )

        self.statusChanged.emit(
            "stopped"
        )

    def is_running(
        self,
    ) -> bool:
        return bool(
            self._running
            and self.timer.isActive()
        )

    def cooldown_remaining_seconds(
        self,
    ) -> float:
        return max(
            0.0,
            self._retry_not_before
            - time.monotonic(),
        )

    def _record_failure(
        self,
        code: str,
    ) -> None:
        if code not in SMTP_ERROR_CODES:
            code = "generic"

        self._failure_count = min(
            self._failure_count + 1,
            31,
        )

        exponent = min(
            self._failure_count - 1,
            20,
        )

        delay = min(
            MAIL_BACKOFF_INITIAL_SECONDS
            * (2 ** exponent),
            MAIL_BACKOFF_MAX_SECONDS,
        )

        self._retry_not_before = (
            time.monotonic()
            + delay
        )
        self._last_error_code = code
        self._cycle_failure_recorded = True

        self.statusChanged.emit(
            "smtp-error:"
            + code
        )

        self._log(
            "MAIL_BACKOFF "
            f"code={code} "
            f"seconds={delay}"
        )

    def _record_success(self) -> None:
        self._failure_count = 0
        self._retry_not_before = 0.0
        self._last_error_code = ""
        self._cycle_failure_recorded = False

        self.statusChanged.emit(
            "smtp-ok"
        )

    def _collect_status_output(
        self,
    ) -> None:
        try:
            chunk = bytes(
                self.process
                .readAllStandardOutput()
            )
        except Exception:
            self._status_overflow = True
            return

        remaining = (
            MAIL_STATUS_MAX_BYTES
            - len(self._status_buffer)
        )

        if len(chunk) > remaining:
            self._status_overflow = True
            self._status_buffer.extend(
                chunk[:max(0, remaining)]
            )
            return

        self._status_buffer.extend(
            chunk
        )

    def _discard_stderr(self) -> None:
        try:
            self.process.readAllStandardError()
        except Exception:
            pass

    def run_cycle(
        self,
    ) -> None:
        if not self._running:
            return

        if self.cooldown_remaining_seconds() > 0:
            self.cycleCompleted.emit()
            return

        if (
            mail_transport_ready()
            and self.process.state()
            == QProcess.ProcessState
            .NotRunning
            and mail_dispatch
            .due_exists()
        ):
            self._start_process()

        self.cycleCompleted.emit()

    def _start_process(
        self,
    ) -> None:
        if not MAIL_SCRIPT.exists():
            self.statusChanged.emit(
                "mail-script-missing"
            )

            return

        self._status_buffer.clear()
        self._status_overflow = False
        self._cycle_failure_recorded = False

        self.process.setProcessEnvironment(
            self._environment()
        )

        self.process.setWorkingDirectory(
            str(
                CODE_ROOT
            )
        )

        self.process.setProgram(
            sys.executable
        )

        self.process.setArguments(
            [
                str(
                    MAIL_SCRIPT
                ),
            ]
        )

        self.process.start()

    def _finished(
        self,
        exit_code: int,
        _exit_status,
    ) -> None:
        self._collect_status_output()
        self._discard_stderr()

        payload = bytes(
            self._status_buffer
        )
        overflow = (
            self._status_overflow
        )

        self._status_buffer.clear()
        self._status_overflow = False

        if not self._running:
            return

        frame = (
            None
            if overflow
            else parse_status_frame(
                payload
            )
        )

        if (
            exit_code == 0
            and frame
            == (
                "ok",
                "ok",
            )
        ):
            self._record_success()
            self._log(
                "MAIL_FINISHED status=ok"
            )
            return

        code = (
            frame[1]
            if frame is not None
            and frame[0] == "error"
            else "generic"
        )

        if not self._cycle_failure_recorded:
            self._record_failure(
                code
            )

        self._log(
            "MAIL_FINISHED "
            f"status=error code={code}"
        )

    def _error(
        self,
        _error,
    ) -> None:
        if (
            self._running
            and not self
            ._cycle_failure_recorded
        ):
            self._record_failure(
                "generic"
            )

        self._log(
            "MAIL_PROCESS_ERROR code=generic"
        )

    def _log(
        self,
        message: str,
    ) -> None:
        try:
            directory = (
                runtime_config
                .logs_dir()
            )

            directory.mkdir(
                parents=True,
                exist_ok=True,
                mode=0o700,
            )

            path = (
                directory
                / "mail_scheduler.log"
            )

            with path.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    dt.datetime.now()
                    .isoformat()
                    + " "
                    + message
                    + "\n"
                )

        except OSError:
            pass


def selftest() -> int:
    scheduler = (
        MailDeliveryScheduler(
            interval_ms=30000
        )
    )

    assert (
        scheduler.interval_ms
        == 30000
    )

    assert not (
        scheduler.is_running()
    )

    print(
        "MAIL_SCHEDULER_INTERVAL_MS=30000"
    )

    print(
        "MAIL_TRANSPORT_READY="
        + (
            "YES"
            if mail_transport_ready()
            else "NO"
        )
    )

    print(
        "MAIL_SCHEDULER_SELFTEST=PASS"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        selftest()
    )
