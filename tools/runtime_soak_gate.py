#!/usr/bin/env python3
"""Isolated long-running UI/runtime stability gate for Hatırlatıcı."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import gc
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from unittest import mock


EXIT_TRUE_FAILURE = 41


def _rss_kib() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(
            encoding="utf-8"
        ).splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _release_server(server, server_name: str) -> None:
    from PyQt6.QtNetwork import QLocalServer

    server.close()
    handle = getattr(
        server,
        "_lifetime_lock_handle",
        None,
    )
    if handle is not None:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_UN,
        )
        handle.close()
    QLocalServer.removeServer(server_name)


def run(
    duration_seconds: int,
    reminder_count: int,
    requested_reminders: int,
) -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="hatirlatici-soak-"
    ) as temp_name:
        xdg_root = Path(temp_name)
        isolated_dirs = {
            "XDG_CONFIG_HOME": xdg_root / "config",
            "XDG_DATA_HOME": xdg_root / "data",
            "XDG_STATE_HOME": xdg_root / "state",
            "XDG_CACHE_HOME": xdg_root / "cache",
            "XDG_RUNTIME_DIR": xdg_root / "runtime",
            "HOME": xdg_root / "home",
            "TMPDIR": xdg_root / "tmp",
        }
        for env_name, directory in isolated_dirs.items():
            directory.mkdir(
                parents=True,
                exist_ok=True,
                mode=0o700,
            )
            directory.chmod(0o700)
            os.environ[env_name] = str(directory)
        tempfile.tempdir = str(
            isolated_dirs["TMPDIR"]
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

        code_root_override = os.environ.get(
            "HATIRLATICI_SOAK_CODE_ROOT",
            "",
        ).strip()
        if code_root_override:
            project_root = Path(code_root_override).resolve()
            code_root_source = "INSTALLED_OVERRIDE"
        else:
            project_root = Path(__file__).resolve().parent.parent
            code_root_source = "CHECKOUT"
        if not (
            (project_root / "runtime_config.py").is_file()
            and (project_root / "ui_v2" / "hatirlatici_ultimate.py").is_file()
        ):
            print("SOAK_GATE=FAIL_INVALID_CODE_ROOT", file=sys.stderr)
            return EXIT_TRUE_FAILURE
        ui_root = project_root / "ui_v2"
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(ui_root))

        from PyQt6.QtCore import (
            QCoreApplication,
            QEvent,
            QEventLoop,
            QTimer,
        )
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

        import runtime_config
        import core_v2 as core
        from hatirlatici_ultimate import (
            FinalPolishWindow,
            UltimateEditDialog,
            acquire_single_instance,
        )

        runtime_paths = (
            runtime_config.config_dir(),
            runtime_config.data_dir(),
            runtime_config.state_dir(),
            core.ROOT,
            core.MAIL_CSV,
            core.PC_CSV,
            core.HISTORY_CSV,
            core.SETTINGS_JSON,
            Path(os.environ["XDG_CACHE_HOME"]),
            Path(os.environ["XDG_RUNTIME_DIR"]),
            Path(os.environ["HOME"]),
            Path(os.environ["TMPDIR"]),
        )
        if not all(
            _inside(Path(path), xdg_root)
            for path in runtime_paths
        ):
            failures.append("xdg-isolation")

        runtime_config.save_settings(
            {
                "default_channel": "pc",
                "language": "en",
                "onboarding_completed": True,
                "profile_name": "Alex",
            }
        )
        core.migrate_mail_schema()
        core.ensure_pc_schema()
        core.ensure_history_schema()

        now = dt.datetime.now().replace(
            second=0,
            microsecond=0,
        )
        pair_ids: list[str] = []
        seed_started = time.monotonic()
        for index in range(reminder_count):
            pair_ids.append(
                core.save_group(
                    pair_id=None,
                    channel=(
                        "both"
                        if index % 11 == 0
                        else "pc"
                    ),
                    subject=f"Sample reminder {index + 1:03d}",
                    body="Synthetic release stability data",
                    run_at=(
                        now
                        + dt.timedelta(
                            minutes=10 + index,
                        )
                    ),
                    repeat=(
                        "weekly"
                        if index % 7 == 0
                        else "once"
                    ),
                    category=core.CATEGORIES[
                        index % len(core.CATEGORIES)
                    ],
                )
            )

        completed_count = min(20, reminder_count // 4)
        for pair_id in pair_ids[:completed_count]:
            core.complete_group(pair_id)
        seed_ms = int(
            (time.monotonic() - seed_started) * 1000
        )

        group_count = len(core.load_groups())
        active_group_count = len(
            core.load_groups(active_only=True)
        )
        history_count = len(core.load_history())
        recurring_completed = sum(
            1
            for index in range(completed_count)
            if index % 7 == 0
        )
        expected_active_group_count = (
            reminder_count
            - completed_count
            + recurring_completed
        )
        # Completion retains the original disabled row so history links are
        # stable, while recurring completions advance and stay active.
        if group_count != reminder_count:
            failures.append("group-count")
        if active_group_count != expected_active_group_count:
            failures.append("active-group-count")
        if history_count != completed_count:
            failures.append("history-count")

        app = QApplication.instance() or QApplication(
            ["hatirlatici-runtime-soak"]
        )
        app.setQuitOnLastWindowClosed(False)

        def flush_events() -> None:
            app.processEvents()
            QCoreApplication.sendPostedEvents(
                None,
                QEvent.Type.DeferredDelete,
            )
            app.processEvents()

        server_name = (
            "hat-soak-"
            + uuid.uuid4().hex[:12]
        )
        owner = None
        contender = None
        try:
            owner, forwarded = acquire_single_instance(
                server_name,
                b"raise",
            )
            if owner is None or forwarded:
                failures.append("single-instance-owner")
            else:
                contender, contender_forwarded = acquire_single_instance(
                    server_name,
                    b"raise",
                )
                if contender is not None or not contender_forwarded:
                    failures.append("single-instance-forward")
        finally:
            if contender is not None:
                _release_server(
                    contender,
                    server_name,
                )
            if owner is not None:
                _release_server(
                    owner,
                    server_name,
                )

        with mock.patch.object(
            QSystemTrayIcon,
            "isSystemTrayAvailable",
            return_value=False,
        ):
            cold_started = time.monotonic()
            window = FinalPolishWindow()
            window.resize(1000, 700)
            window.show()
            flush_events()
            cold_launch_ms = int(
                (time.monotonic() - cold_started) * 1000
            )
            if cold_launch_ms > 15000:
                failures.append("cold-launch")

            navigation_started = time.monotonic()
            navigation_switches = 0
            for _ in range(4):
                for page in (
                    "today",
                    "reminders",
                    "history",
                    "settings",
                ):
                    window.switch_page(page)
                    flush_events()
                    navigation_switches += 1
            navigation_ms = int(
                (time.monotonic() - navigation_started) * 1000
            )

            sample = core.load_groups()[0]
            for _ in range(8):
                dialog = UltimateEditDialog(window, sample)
                dialog.show()
                flush_events()
                dialog.reject()
                dialog.deleteLater()
                flush_events()

            for language in (
                "tr",
                "de",
                "es",
                "ru",
                "en",
            ):
                window._change_language(language)
                flush_events()
                if window.language != language:
                    failures.append("language-switch")
                    break

            window.hide()
            flush_events()
            if window.isVisible():
                failures.append("window-hide")
            window._raise_window()
            flush_events()
            if not window.isVisible():
                failures.append("window-restore")

            gc.collect()
            flush_events()
            rss_start_kib = _rss_kib()
            rss_samples: list[int] = []
            if rss_start_kib is None:
                failures.append("rss-unavailable")
            else:
                rss_samples.append(rss_start_kib)

            def sample_rss() -> None:
                value = _rss_kib()
                if value is None:
                    if "rss-unavailable" not in failures:
                        failures.append("rss-unavailable")
                else:
                    rss_samples.append(value)

            cpu_started = time.process_time()
            idle_started = time.monotonic()

            loop = QEventLoop()
            sampler = QTimer()
            sampler.setInterval(
                max(
                    1000,
                    min(
                        60000,
                        duration_seconds * 1000 // 6,
                    ),
                )
            )
            sampler.timeout.connect(
                sample_rss
            )
            sampler.start()
            QTimer.singleShot(
                duration_seconds * 1000,
                loop.quit,
            )
            loop.exec()
            sampler.stop()

            idle_elapsed = time.monotonic() - idle_started
            cpu_seconds = time.process_time() - cpu_started
            rss_end_kib = _rss_kib()
            if rss_end_kib is None:
                if "rss-unavailable" not in failures:
                    failures.append("rss-unavailable")
            else:
                rss_samples.append(rss_end_kib)
            rss_growth_kib = (
                rss_end_kib - rss_start_kib
                if (
                    rss_start_kib is not None
                    and rss_end_kib is not None
                )
                else None
            )
            rss_peak_kib = (
                max(rss_samples)
                if rss_samples
                else None
            )
            cpu_ratio = (
                cpu_seconds / idle_elapsed
                if idle_elapsed > 0
                else 1.0
            )

            if (
                rss_growth_kib is not None
                and rss_growth_kib > 65536
            ):
                failures.append("idle-memory-growth")
            if (
                rss_start_kib is not None
                and rss_peak_kib is not None
                and rss_peak_kib - rss_start_kib > 65536
            ):
                failures.append("idle-memory-peak")
            if cpu_ratio > 0.15:
                failures.append("idle-cpu")
            if idle_elapsed + 0.5 < duration_seconds:
                failures.append("idle-duration")

            window.close()
            window.deleteLater()
            flush_events()

        print(f"SOAK_CODE_ROOT_SOURCE={code_root_source}")
        print(f"SOAK_DURATION_SECONDS={idle_elapsed:.2f}")
        print(f"REQUESTED_REMINDERS={requested_reminders}")
        print(f"EFFECTIVE_REMINDERS={reminder_count}")
        print(f"REMINDER_GROUPS={group_count}")
        print(f"ACTIVE_GROUPS={active_group_count}")
        print(f"COMPLETED_EVENTS={completed_count}")
        print(f"HISTORY_EVENTS={history_count}")
        print(f"SEED_MS={seed_ms}")
        print(f"COLD_LAUNCH_MS={cold_launch_ms}")
        print(f"NAVIGATION_SWITCHES={navigation_switches}")
        print(f"NAVIGATION_MS={navigation_ms}")
        print(
            "RSS_START_KIB="
            + (
                str(rss_start_kib)
                if rss_start_kib is not None
                else "UNAVAILABLE"
            )
        )
        print(
            "RSS_END_KIB="
            + (
                str(rss_end_kib)
                if rss_end_kib is not None
                else "UNAVAILABLE"
            )
        )
        print(
            "RSS_GROWTH_KIB="
            + (
                str(rss_growth_kib)
                if rss_growth_kib is not None
                else "UNAVAILABLE"
            )
        )
        print(
            "RSS_PEAK_KIB="
            + (
                str(rss_peak_kib)
                if rss_peak_kib is not None
                else "UNAVAILABLE"
            )
        )
        print(f"IDLE_CPU_SECONDS={cpu_seconds:.3f}")
        print(f"IDLE_CPU_RATIO={cpu_ratio:.6f}")
        print(f"TRUE_FAILURES={len(set(failures))}")
        for failure in sorted(set(failures)):
            print(f"FAILURE={failure}")

        return EXIT_TRUE_FAILURE if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=1800,
    )
    parser.add_argument(
        "--reminders",
        type=int,
        default=120,
    )
    args = parser.parse_args()
    duration = max(1, int(args.duration_seconds))
    requested_reminders = int(args.reminders)
    reminder_count = max(100, requested_reminders)
    try:
        return run(
            duration,
            reminder_count,
            requested_reminders,
        )
    except Exception as exc:
        print(
            "SOAK_UNHANDLED_EXCEPTION="
            + type(exc).__name__
        )
        print("TRUE_FAILURES=1")
        print("FAILURE=unhandled-exception")
        return EXIT_TRUE_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
