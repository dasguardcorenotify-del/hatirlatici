import datetime as dt
import tempfile
import unittest
from pathlib import Path

import core_v2 as core
import notification_action_worker as worker


class ActionTests(unittest.TestCase):
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

    def tearDown(self):
        self.temp.cleanup()

    def claimed(
        self,
        repeat="once",
    ):
        future = (
            dt.datetime.now()
            .replace(
                second=0,
                microsecond=0,
            )
            + dt.timedelta(hours=1)
        )

        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="ACTION TEST",
            body="TEST",
            run_at=future,
            repeat=repeat,
        )

        scheduled = (
            core.fmt_dt(future)
        )

        lease = core.fmt_dt(
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
                    row["lease_until"] = (
                        lease
                    )

            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(fields),
                rows,
            )

        return (
            pair,
            scheduled,
            lease,
        )

    def test_snooze(self):
        pair, scheduled, lease = (
            self.claimed()
        )

        ok = worker.finalize_delivery(
            pair,
            scheduled,
            lease,
            "snooze",
        )

        self.assertTrue(ok)

        group = {
            g["pair_id"]: g
            for g in core.load_groups()
        }[pair]

        row = group["pc_row"]

        self.assertEqual(
            row["enabled"],
            "1",
        )

        self.assertEqual(
            row["lease_until"],
            "",
        )

        self.assertTrue(
            row["snooze_until"]
        )

        self.assertEqual(
            row["send_count"],
            "1",
        )

        self.assertEqual(
            core.load_history()[0][
                "action"
            ],
            "snoozed",
        )

    def test_complete_once(self):
        pair, scheduled, lease = (
            self.claimed("once")
        )

        ok = worker.finalize_delivery(
            pair,
            scheduled,
            lease,
            "complete",
        )

        self.assertTrue(ok)

        group = {
            g["pair_id"]: g
            for g in core.load_groups()
        }[pair]

        row = group["pc_row"]

        self.assertEqual(
            row["enabled"],
            "0",
        )

        self.assertEqual(
            row["next_run"],
            "",
        )

        self.assertEqual(
            row["lease_until"],
            "",
        )

        self.assertEqual(
            row["snooze_until"],
            "",
        )

    def test_sent_recurring_advances(self):
        pair, scheduled, lease = (
            self.claimed("daily")
        )

        ok = worker.finalize_delivery(
            pair,
            scheduled,
            lease,
            "sent",
        )

        self.assertTrue(ok)

        group = {
            g["pair_id"]: g
            for g in core.load_groups()
        }[pair]

        row = group["pc_row"]

        nxt = core.parse_dt(
            row["next_run"]
        )

        self.assertIsNotNone(nxt)

        self.assertGreater(
            nxt,
            dt.datetime.now(),
        )

    def test_stale_worker_cannot_overwrite(self):
        pair, scheduled, lease = (
            self.claimed()
        )

        ok = worker.finalize_delivery(
            pair,
            scheduled,
            "2099-01-01 00:00",
            "sent",
        )

        self.assertFalse(ok)

    def test_lease_is_not_snooze(self):
        pair, _, lease = (
            self.claimed()
        )

        group = {
            g["pair_id"]: g
            for g in core.load_groups()
        }[pair]

        row = group["pc_row"]

        self.assertEqual(
            row["lease_until"],
            lease,
        )

        self.assertEqual(
            row["snooze_until"],
            "",
        )


if __name__ == "__main__":
    unittest.main()
