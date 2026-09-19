import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

import mail_dispatch
import mail_scheduler
import smtp_transport


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class MailStatusChannelTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def scheduler(self):
        value = (
            mail_scheduler
            .MailDeliveryScheduler()
        )
        value._log = mock.Mock()
        return value

    def test_error_frames_are_bounded_and_round_trip(
        self,
    ):
        for code in sorted(
            mail_scheduler
            .SMTP_ERROR_CODES
        ):
            with self.subTest(
                code=code
            ):
                frame = (
                    mail_dispatch
                    .encode_status_line(
                        mail_dispatch
                        .DispatchResult(
                            exit_code=20,
                            status="error",
                            code=code,
                        )
                    )
                )

                self.assertLessEqual(
                    len(frame),
                    mail_scheduler
                    .MAIL_STATUS_MAX_BYTES,
                )
                self.assertEqual(
                    mail_scheduler
                    .parse_status_frame(
                        frame
                    ),
                    (
                        "error",
                        code,
                    ),
                )

                for secret in (
                    b"pair-id",
                    b"private subject",
                    b"credential",
                ):
                    self.assertNotIn(
                        secret,
                        frame,
                    )

    def test_unknown_error_is_reduced_to_generic(
        self,
    ):
        frame = (
            mail_dispatch
            .encode_status_line(
                mail_dispatch
                .DispatchResult(
                    exit_code=20,
                    status="error",
                    code=(
                        "server said secret"
                    ),
                )
            )
        )

        self.assertEqual(
            mail_scheduler
            .parse_status_frame(frame),
            (
                "error",
                "generic",
            ),
        )
        self.assertNotIn(
            b"secret",
            frame,
        )

        enum_frame = (
            mail_dispatch
            .encode_status_line(
                mail_dispatch
                .DispatchResult(
                    exit_code=20,
                    status="error",
                    code=(
                        smtp_transport
                        .MailErrorCode.AUTH
                    ),
                )
            )
        )

        self.assertEqual(
            mail_scheduler
            .parse_status_frame(
                enum_frame
            ),
            (
                "error",
                "auth",
            ),
        )

    def test_malformed_extra_or_oversize_output_is_rejected(
        self,
    ):
        good = (
            mail_dispatch
            .encode_status_line(
                mail_dispatch
                .DispatchResult(
                    exit_code=0,
                    status="ok",
                    code="ok",
                )
            )
        )

        malformed = (
            b"noise" + good,
            good + b"extra",
            good + b"second\n",
            b"MAIL_STATUS_V1 {}\n",
            b"MAIL_STATUS_V1 \xff\n",
            (
                b'MAIL_STATUS_V1 {"code":"ok", '
                b'"status":"ok","version":1}\n'
            ),
            (
                b'MAIL_STATUS_V1 {"code":"ok",'
                b'"code":"ok","status":"ok",'
                b'"version":1}\n'
            ),
            b"x" * (
                mail_scheduler
                .MAIL_STATUS_MAX_BYTES
                + 1
            ),
        )

        for payload in malformed:
            with self.subTest(
                payload=payload[:32]
            ):
                self.assertIsNone(
                    mail_scheduler
                    .parse_status_frame(
                        payload
                    )
                )

    def test_backoff_doubles_caps_and_success_resets(
        self,
    ):
        scheduler = self.scheduler()
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        now = 1000.0

        for expected_count in range(
            1,
            10,
        ):
            with mock.patch.object(
                mail_scheduler.time,
                "monotonic",
                return_value=now,
            ):
                scheduler._record_failure(
                    "auth"
                )

            expected_delay = min(
                mail_scheduler
                .MAIL_BACKOFF_INITIAL_SECONDS
                * (
                    2
                    ** (
                        expected_count
                        - 1
                    )
                ),
                mail_scheduler
                .MAIL_BACKOFF_MAX_SECONDS,
            )

            self.assertEqual(
                scheduler
                ._retry_not_before,
                now + expected_delay,
            )

        self.assertEqual(
            statuses[-1],
            "smtp-error:auth",
        )
        self.assertEqual(
            scheduler._failure_count,
            9,
        )

        scheduler._record_success()

        self.assertEqual(
            scheduler._failure_count,
            0,
        )
        self.assertEqual(
            scheduler._retry_not_before,
            0.0,
        )
        self.assertEqual(
            statuses[-1],
            "smtp-ok",
        )

    def test_cooldown_suppresses_dispatch_cycle(
        self,
    ):
        scheduler = self.scheduler()
        scheduler._running = True
        scheduler._retry_not_before = 200.0

        with (
            mock.patch.object(
                mail_scheduler.time,
                "monotonic",
                return_value=100.0,
            ),
            mock.patch.object(
                mail_scheduler,
                "mail_transport_ready",
            ) as ready,
            mock.patch.object(
                mail_scheduler
                .mail_dispatch,
                "due_exists",
            ) as due,
            mock.patch.object(
                scheduler,
                "_start_process",
            ) as start,
        ):
            scheduler.run_cycle()

        ready.assert_not_called()
        due.assert_not_called()
        start.assert_not_called()

    def test_finished_emits_safe_error_code_and_resets_on_ok(
        self,
    ):
        scheduler = self.scheduler()
        scheduler._running = True
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        scheduler._status_buffer.extend(
            mail_dispatch
            .encode_status_line(
                mail_dispatch
                .DispatchResult(
                    exit_code=20,
                    status="error",
                    code="tls",
                )
            )
        )

        with mock.patch.object(
            mail_scheduler.time,
            "monotonic",
            return_value=500.0,
        ), mock.patch.object(
            scheduler,
            "_collect_status_output",
        ), mock.patch.object(
            scheduler,
            "_discard_stderr",
        ):
            scheduler._finished(
                20,
                None,
            )

        self.assertEqual(
            statuses[-1],
            "smtp-error:tls",
        )
        self.assertEqual(
            scheduler._last_error_code,
            "tls",
        )

        scheduler._status_buffer.extend(
            mail_dispatch
            .encode_status_line(
                mail_dispatch
                .DispatchResult(
                    exit_code=0,
                    status="ok",
                    code="ok",
                )
            )
        )
        with (
            mock.patch.object(
                scheduler,
                "_collect_status_output",
            ),
            mock.patch.object(
                scheduler,
                "_discard_stderr",
            ),
        ):
            scheduler._finished(
                0,
                None,
            )

        self.assertEqual(
            statuses[-1],
            "smtp-ok",
        )
        self.assertEqual(
            scheduler._failure_count,
            0,
        )

    def test_fresh_dispatch_stdout_is_exact_protocol_frame(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            environment = os.environ.copy()
            environment.update(
                {
                    "XDG_CONFIG_HOME": str(
                        base / "config"
                    ),
                    "XDG_DATA_HOME": str(
                        base / "data"
                    ),
                    "XDG_STATE_HOME": str(
                        base / "state"
                    ),
                    "PYTHONPATH": os.pathsep.join(
                        (
                            str(ROOT),
                            str(ROOT / "ui_v2"),
                        )
                    ),
                }
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "mail_dispatch.py"
                    ),
                ],
                cwd=str(ROOT),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            0,
        )
        self.assertEqual(
            result.stderr,
            b"",
        )
        self.assertEqual(
            mail_scheduler
            .parse_status_frame(
                result.stdout
            ),
            (
                "ok",
                "ok",
            ),
        )


if __name__ == "__main__":
    unittest.main()
