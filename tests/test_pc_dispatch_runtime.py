import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import core_v2 as core
import notification_ipc
import pc_notify


class FakeStdin:
    def __init__(self):
        self.payload = b""
        self.closed = False

    def write(self, value):
        self.payload += value
        return len(value)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class FakeProcess:
    wait_calls = 0
    timeouts = []
    instances = []

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.returncode = 0
        self.argv = args[0]
        self.kwargs = kwargs
        self.stdin = FakeStdin()

        FakeProcess.instances.append(
            self
        )

    def wait(
        self,
        timeout=None,
    ):
        if timeout is None:
            raise AssertionError(
                "Worker wait bounded olmalı."
            )

        FakeProcess.wait_calls += 1
        FakeProcess.timeouts.append(
            timeout
        )

        return 0

    def kill(self):
        pass


class FailedProcess(
    FakeProcess
):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(
        self,
        timeout=None,
    ):
        self.returncode = 9
        return self.returncode


class StubbornProcess:
    def __init__(self):
        self.returncode = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9

    def wait(self, timeout=None):
        self.wait_calls += 1

        if self.returncode is None:
            raise (
                pc_notify
                .subprocess
                .TimeoutExpired(
                    "worker",
                    timeout,
                )
            )

        return self.returncode


class TimeoutProcess(
    StubbornProcess
):
    instances = []

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__()
        self.argv = args[0]
        self.kwargs = kwargs
        self.stdin = FakeStdin()
        self.__class__.instances.append(
            self
        )


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = (
            tempfile.TemporaryDirectory()
        )

        root = Path(
            self.temp.name
        )

        core.ROOT = root
        core.MAIL_CSV = root / "mail.csv"
        core.PC_CSV = root / "pc.csv"
        core.HISTORY_CSV = root / "history.csv"

        core.MAIL_LOCK = root / ".mail.lock"
        core.PC_LOCK = root / ".pc.lock"
        core.HISTORY_LOCK = root / ".history.lock"

        core.SETTINGS_JSON = (
            root / "settings.json"
        )

        core.DATA_BACKUPS = (
            root / "backups"
        )

        core.migrate_mail_schema()
        core.ensure_pc_schema()
        core.ensure_history_schema()

        pc_notify.core = core

    def tearDown(self):
        pc_notify._ACTIVE_WORKERS.clear()
        pc_notify._SHUTDOWN_REQUESTED = False
        self.temp.cleanup()

    def make_due(
        self,
        *,
        subject="DUE TEST",
        body="BODY",
    ):
        future = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(minutes=2)
        )

        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject=subject,
            body=body,
            run_at=future,
            repeat="once",
        )

        due = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            - dt.timedelta(minutes=1)
        )

        with core.exclusive(
            core.PC_LOCK
        ):
            fields, rows = core.read_csv(
                core.PC_CSV,
                core.FIELDS,
            )

            for row in rows:
                if row.get("pair_id") == pair:
                    row["next_run"] = (
                        core.fmt_dt(due)
                    )

            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(fields),
                rows,
            )

        return pair

    def test_parent_waits_for_worker(self):
        future = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(minutes=2)
        )

        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="DISPATCH TEST",
            body="TEST",
            run_at=future,
            repeat="once",
        )

        due = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            - dt.timedelta(minutes=1)
        )

        with core.exclusive(
            core.PC_LOCK
        ):
            fields, rows = core.read_csv(
                core.PC_CSV,
                core.FIELDS,
            )

            for row in rows:
                if (
                    row.get("pair_id")
                    == pair
                ):
                    row["next_run"] = (
                        core.fmt_dt(due)
                    )

            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(fields),
                rows,
            )

        FakeProcess.wait_calls = 0
        FakeProcess.timeouts = []
        FakeProcess.instances = []

        with mock.patch.object(
            pc_notify.subprocess,
            "Popen",
            FakeProcess,
        ):
            rc = pc_notify.run()

        self.assertEqual(
            rc,
            0,
        )

        self.assertEqual(
            FakeProcess.wait_calls,
            1,
        )

        self.assertTrue(
            FakeProcess.timeouts[0]
            <= pc_notify
            .GLOBAL_WORKER_DEADLINE_SECONDS
        )

        process = (
            FakeProcess.instances[0]
        )

        self.assertNotIn(
            "DISPATCH TEST",
            process.argv,
        )

        self.assertNotIn(
            "TEST",
            process.argv,
        )

        self.assertNotIn(
            "DISPATCH TEST",
            str(process.kwargs),
        )

        self.assertNotIn(
            "TEST",
            str(process.kwargs),
        )

        self.assertNotIn(
            "env",
            process.kwargs,
        )

        self.assertEqual(
            len(process.argv),
            5,
        )

        self.assertTrue(
            process.stdin.closed
        )

        subject, body, token = (
            notification_ipc
            .decode_payload(
                process.stdin.payload
            )
        )

        self.assertEqual(
            (
                subject,
                body,
            ),
            (
                "DISPATCH TEST",
                "TEST",
            ),
        )

        self.assertNotIn(
            token,
            process.argv,
        )

        self.assertNotIn(
            token,
            str(process.kwargs),
        )

    def test_active_lease_prevents_duplicate(self):
        future = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(minutes=2)
        )

        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="LEASE TEST",
            body="TEST",
            run_at=future,
            repeat="once",
        )

        due = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            - dt.timedelta(minutes=1)
        )

        lease = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(minutes=2)
        )

        with core.exclusive(
            core.PC_LOCK
        ):
            fields, rows = core.read_csv(
                core.PC_CSV,
                core.FIELDS,
            )

            for row in rows:
                if (
                    row.get("pair_id")
                    == pair
                ):
                    row["next_run"] = (
                        core.fmt_dt(due)
                    )

                    row["lease_until"] = (
                        core.fmt_dt(lease)
                    )

            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(fields),
                rows,
            )

        with mock.patch.object(
            pc_notify.subprocess,
            "Popen",
        ) as popen:
            rc = pc_notify.run()

        self.assertEqual(rc, 0)

        popen.assert_not_called()

    def test_worker_failure_is_aggregated_and_lease_released(
        self,
    ):
        pair = self.make_due(
            subject="FAILURE TEST",
            body="PRIVATE BODY",
        )

        with mock.patch.object(
            pc_notify.subprocess,
            "Popen",
            FailedProcess,
        ):
            rc = pc_notify.run()

        self.assertEqual(
            rc,
            pc_notify
            .PC_NOTIFY_WORKER_FAILURE,
        )

        group = {
            item["pair_id"]: item
            for item in core.load_groups()
        }[pair]

        self.assertEqual(
            group["pc_row"][
                "lease_until"
            ],
            "",
        )

    def test_worker_timeout_is_aggregated_killed_and_reaped(
        self,
    ):
        pair = self.make_due(
            subject="TIMEOUT TEST",
            body="PRIVATE TIMEOUT BODY",
        )
        TimeoutProcess.instances = []

        with (
            mock.patch.object(
                pc_notify.subprocess,
                "Popen",
                TimeoutProcess,
            ),
            mock.patch.object(
                pc_notify,
                "GLOBAL_WORKER_DEADLINE_SECONDS",
                0,
            ),
            mock.patch.object(
                pc_notify,
                "WORKER_TERMINATE_GRACE_SECONDS",
                0.01,
            ),
            mock.patch.object(
                pc_notify,
                "WORKER_KILL_GRACE_SECONDS",
                0.01,
            ),
        ):
            rc = pc_notify.run()

        self.assertEqual(
            rc,
            pc_notify
            .PC_NOTIFY_WORKER_FAILURE,
        )

        process = (
            TimeoutProcess.instances[0]
        )

        self.assertEqual(
            process.terminate_calls,
            1,
        )
        self.assertEqual(
            process.kill_calls,
            1,
        )
        self.assertEqual(
            process.returncode,
            -9,
        )

        group = {
            item["pair_id"]: item
            for item in core.load_groups()
        }[pair]

        self.assertEqual(
            group["pc_row"][
                "lease_until"
            ],
            "",
        )

    def test_shutdown_terminates_kills_and_reaps_children(
        self,
    ):
        process = StubbornProcess()
        pc_notify._ACTIVE_WORKERS[:] = [
            process,
        ]

        with (
            mock.patch.object(
                pc_notify,
                "WORKER_TERMINATE_GRACE_SECONDS",
                0.01,
            ),
            mock.patch.object(
                pc_notify,
                "WORKER_KILL_GRACE_SECONDS",
                0.01,
            ),
        ):
            pc_notify._request_shutdown(
                None,
                None,
            )

        self.assertTrue(
            pc_notify
            ._SHUTDOWN_REQUESTED
        )
        self.assertEqual(
            process.terminate_calls,
            1,
        )
        self.assertEqual(
            process.kill_calls,
            1,
        )
        self.assertGreaterEqual(
            process.wait_calls,
            2,
        )
        self.assertEqual(
            pc_notify._ACTIVE_WORKERS,
            [],
        )

    def test_real_child_is_reaped_during_shutdown(
        self,
    ):
        process = pc_notify._spawn_worker(
            [
                pc_notify.sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ]
        )

        process.stdin.close()

        try:
            with (
                mock.patch.object(
                    pc_notify,
                    "WORKER_TERMINATE_GRACE_SECONDS",
                    0.2,
                ),
                mock.patch.object(
                    pc_notify,
                    "WORKER_KILL_GRACE_SECONDS",
                    0.2,
                ),
            ):
                pc_notify._request_shutdown(
                    None,
                    None,
                )

            self.assertIsNotNone(
                process.poll()
            )
            self.assertEqual(
                pc_notify._ACTIVE_WORKERS,
                [],
            )
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=1)


if __name__ == "__main__":
    unittest.main()
