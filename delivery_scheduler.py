#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import os
import sys
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
    QCoreApplication,
    QObject,
    QProcess,
    QProcessEnvironment,
    QTimer,
    pyqtSignal,
)

import background_portal
import l10n
import runtime_config
import core_v2 as core


PC_SCRIPT = (
    CODE_ROOT
    / "pc_notify.py"
)

# E-posta transportu 4C5'te
# Python-native hale geldikten sonra aktive edilir.
MAIL_TRANSPORT_FLAG = (
    "mail_transport_v2_ready"
)

PC_EXIT_STATUS_CODES = {
    20: "worker",
    21: "interrupted",
}


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


def _row_due(
    row: dict,
    now: dt.datetime,
) -> bool:
    if (
        str(
            row.get(
                "enabled",
                "",
            )
        ).strip()
        != "1"
    ):
        return False

    scheduled = (
        core.parse_dt(
            row.get(
                "next_run",
                "",
            )
        )
    )

    if (
        scheduled is None
        or scheduled > now
    ):
        return False

    snooze = (
        core.parse_dt(
            row.get(
                "snooze_until",
                "",
            )
        )
    )

    if (
        snooze is not None
        and snooze > now
    ):
        return False

    lease = (
        core.parse_dt(
            row.get(
                "lease_until",
                "",
            )
        )
    )

    if (
        lease is not None
        and lease > now
    ):
        return False

    return True


def pc_due_exists(
    now: dt.datetime | None = None,
) -> bool:
    now = (
        now
        or dt.datetime.now()
    ).replace(
        second=0,
        microsecond=0,
    )

    settings = (
        core.load_settings()
    )

    if core.is_quiet_time(
        now,
        settings,
    ):
        return False

    for group in (
        core.load_groups(
            active_only=True
        )
    ):
        row = group.get(
            "pc_row"
        )

        if (
            isinstance(
                row,
                dict,
            )
            and _row_due(
                row,
                now,
            )
        ):
            return True

    return False


def mail_transport_ready() -> bool:
    settings = (
        runtime_config
        .load_settings()
    )

    return bool(
        settings.get(
            MAIL_TRANSPORT_FLAG,
            False,
        )
    )


class DeliveryScheduler(
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

        self.pc_process = QProcess(
            self
        )

        self.pc_process.setProcessChannelMode(
            QProcess.ProcessChannelMode
            .MergedChannels
        )

        self.pc_process.finished.connect(
            self._pc_finished
        )

        self.pc_process.errorOccurred.connect(
            self._pc_error
        )

        self._running = False

    def _process_environment(
        self,
    ) -> QProcessEnvironment:
        environment = (
            QProcessEnvironment
            .systemEnvironment()
        )

        entries = [
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
            entries.append(
                existing
            )

        environment.insert(
            "PYTHONPATH",
            os.pathsep.join(
                entries
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

        try:
            background_portal.set_status(
                l10n.text(
                    "scheduler_status_monitoring",
                    _runtime_language(),
                )
            )
        except Exception:
            pass

        QTimer.singleShot(
            250,
            self.run_cycle,
        )

    def stop(
        self,
    ) -> None:
        self._running = False

        self.timer.stop()

        if (
            self.pc_process.state()
            != QProcess.ProcessState
            .NotRunning
        ):
            self.pc_process.terminate()

            if not (
                self.pc_process
                .waitForFinished(
                    1500
                )
            ):
                self.pc_process.kill()

                self.pc_process.waitForFinished(
                    1000
                )

        self.statusChanged.emit(
            "stopped"
        )

    def is_running(
        self,
    ) -> bool:
        return (
            self._running
            and self.timer.isActive()
        )

    def run_cycle(
        self,
    ) -> None:
        if not self._running:
            return

        if (
            self.pc_process.state()
            == QProcess.ProcessState
            .NotRunning
            and pc_due_exists()
        ):
            self._start_pc_cycle()

        self.cycleCompleted.emit()

    def _start_pc_cycle(
        self,
    ) -> None:
        if not PC_SCRIPT.exists():
            self.statusChanged.emit(
                "pc-script-missing"
            )
            return

        self.pc_process.setProcessEnvironment(
            self._process_environment()
        )

        self.pc_process.setWorkingDirectory(
            str(
                CODE_ROOT
            )
        )

        self.pc_process.setProgram(
            sys.executable
        )

        self.pc_process.setArguments(
            [
                str(
                    PC_SCRIPT
                ),
            ]
        )

        self.pc_process.start()

    def _pc_finished(
        self,
        exit_code: int,
        _exit_status,
    ) -> None:
        # Drain and discard the merged channel.  Child output is not part of
        # the protocol and may contain an unexpected traceback; never mirror
        # it into persistent logs or a user-facing status.
        try:
            self.pc_process.readAllStandardOutput()
        except Exception:
            pass

        if not self._running:
            self._log(
                "PC_FINISHED status=stopped"
            )
            return

        if exit_code == 0:
            self.statusChanged.emit(
                "pc-ok"
            )
            status_code = "ok"
        else:
            status_code = (
                PC_EXIT_STATUS_CODES
                .get(
                    int(exit_code),
                    "generic",
                )
            )
            self.statusChanged.emit(
                "pc-error:"
                + status_code
            )

        self._log(
            "PC_FINISHED status="
            + status_code
        )

    def _pc_error(
        self,
        _error,
    ) -> None:
        if not self._running:
            self._log(
                "PC_PROCESS_ERROR status=stopped"
            )
            return

        self.statusChanged.emit(
            "pc-error:process"
        )

        self._log(
            "PC_PROCESS_ERROR status=process"
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
                / "scheduler.log"
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


def scheduler_selftest() -> int:
    runtime_config.ensure_runtime_dirs()

    scheduler = (
        DeliveryScheduler(
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
        "INTERNAL_SCHEDULER_INTERVAL_MS=30000"
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
        "INTERNAL_SCHEDULER_SELFTEST=PASS"
    )

    return 0


def manual_e2e() -> int:
    runtime_config.ensure_runtime_dirs()
    language = _runtime_language()

    core.migrate_mail_schema()
    core.ensure_pc_schema()
    core.ensure_history_schema()

    future = (
        dt.datetime.now()
        .replace(
            second=0,
            microsecond=0,
        )
        + dt.timedelta(
            minutes=5
        )
    )

    pair = core.save_group(
        pair_id=None,
        channel="pc",
        subject=l10n.text(
            "scheduler_test_title",
            language,
        ),
        body=l10n.text(
            "scheduler_test_message",
            language,
        ),
        run_at=future,
        repeat="once",
        category="Genel",
    )

    due = (
        dt.datetime.now()
        .replace(
            second=0,
            microsecond=0,
        )
        - dt.timedelta(
            minutes=1
        )
    )

    with core.exclusive(
        core.PC_LOCK
    ):
        fields, rows = (
            core.read_csv(
                core.PC_CSV,
                core.FIELDS,
            )
        )

        for row in rows:
            if (
                row.get(
                    "pair_id"
                )
                == pair
            ):
                row[
                    "next_run"
                ] = (
                    core.fmt_dt(
                        due
                    )
                )

        core.atomic_write(
            core.PC_CSV,
            core.ensure_fields(
                fields
            ),
            rows,
        )

    print(
        "SCHEDULER_E2E_PAIR="
        + str(pair),
        flush=True,
    )

    print(
        "SCHEDULER_E2E_WAITING=YES",
        flush=True,
    )

    app = (
        QCoreApplication.instance()
        or QCoreApplication(
            sys.argv
        )
    )

    scheduler = (
        DeliveryScheduler(
            interval_ms=500
        )
    )

    result = {
        "ok": False,
    }

    poll = QTimer()

    poll.setInterval(
        250
    )

    def check_result():
        events = [
            event
            for event
            in core.load_history()
            if event.get(
                "pair_id"
            ) == pair
            and event.get(
                "channel"
            ) == "pc"
        ]

        if not events:
            return

        action = (
            events[0]
            .get(
                "action"
            )
        )

        print(
            "SCHEDULER_E2E_ACTION="
            + str(action),
            flush=True,
        )

        if action == "completed":
            result[
                "ok"
            ] = True

        poll.stop()
        scheduler.stop()
        app.quit()

    poll.timeout.connect(
        check_result
    )

    timeout = QTimer()

    timeout.setSingleShot(
        True
    )

    timeout.setInterval(
        47000
    )

    def timed_out():
        print(
            "SCHEDULER_E2E_TIMEOUT=YES",
            flush=True,
        )

        poll.stop()
        scheduler.stop()
        app.quit()

    timeout.timeout.connect(
        timed_out
    )

    scheduler.start()
    poll.start()
    timeout.start()

    app.exec()

    if not result[
        "ok"
    ]:
        return 31

    groups = {
        str(
            item[
                "pair_id"
            ]
        ): item
        for item
        in core.load_groups()
    }

    row = (
        groups[
            str(pair)
        ][
            "pc_row"
        ]
    )

    assert (
        row.get(
            "send_count"
        )
        == "1"
    )

    assert (
        row.get(
            "enabled"
        )
        == "0"
    )

    assert not (
        row.get(
            "lease_until"
        )
    )

    print(
        "INTERNAL_SCHEDULER_E2E=PASS"
    )

    print(
        "INTERNAL_SCHEDULER_EXACTLY_ONCE=PASS"
    )

    return 0


def main() -> int:
    args = set(
        sys.argv[1:]
    )

    if "--selftest" in args:
        return scheduler_selftest()

    if "--manual-e2e" in args:
        return manual_e2e()

    return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
