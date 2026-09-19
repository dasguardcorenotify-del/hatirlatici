import os
import unittest
from unittest import mock

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PyQt6.QtWidgets import QApplication

import delivery_scheduler


class DeliverySchedulerStatusTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def scheduler(self):
        scheduler = (
            delivery_scheduler
            .DeliveryScheduler()
        )
        scheduler._log = mock.Mock()
        return scheduler

    def test_nonzero_worker_status_is_observable_and_bounded(
        self,
    ):
        scheduler = self.scheduler()
        scheduler._running = True
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        with mock.patch.object(
            scheduler.pc_process,
            "readAllStandardOutput",
        ):
            scheduler._pc_finished(
                20,
                None,
            )
            scheduler._pc_finished(
                21,
                None,
            )
            scheduler._pc_finished(
                199,
                None,
            )

        self.assertEqual(
            statuses,
            [
                "pc-error:worker",
                "pc-error:interrupted",
                "pc-error:generic",
            ],
        )

    def test_success_is_observable(self):
        scheduler = self.scheduler()
        scheduler._running = True
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        with mock.patch.object(
            scheduler.pc_process,
            "readAllStandardOutput",
        ):
            scheduler._pc_finished(
                0,
                None,
            )

        self.assertEqual(
            statuses,
            [
                "pc-ok",
            ],
        )

    def test_intentional_stop_is_not_reported_as_failure(
        self,
    ):
        scheduler = self.scheduler()
        scheduler._running = False
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        with mock.patch.object(
            scheduler.pc_process,
            "readAllStandardOutput",
        ):
            scheduler._pc_finished(
                21,
                None,
            )
        scheduler._pc_error(
            RuntimeError(
                "private unexpected output"
            )
        )

        self.assertEqual(
            statuses,
            [],
        )

        logged = " ".join(
            call.args[0]
            for call in scheduler
            ._log.call_args_list
        )

        self.assertNotIn(
            "private",
            logged,
        )

    def test_process_error_never_forwards_exception_text(
        self,
    ):
        scheduler = self.scheduler()
        scheduler._running = True
        statuses = []
        scheduler.statusChanged.connect(
            statuses.append
        )

        scheduler._pc_error(
            RuntimeError(
                "credential and body"
            )
        )

        self.assertEqual(
            statuses,
            [
                "pc-error:process",
            ],
        )

        logged = " ".join(
            call.args[0]
            for call in scheduler
            ._log.call_args_list
        )

        self.assertNotIn(
            "credential",
            logged,
        )
        self.assertNotIn(
            "body",
            logged,
        )


if __name__ == "__main__":
    unittest.main()
