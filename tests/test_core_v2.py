import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import core_v2 as core


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)

        core.ROOT = root
        core.MAIL_CSV = root / "mail.csv"
        core.PC_CSV = root / "pc.csv"
        core.HISTORY_CSV = root / "history.csv"

        core.MAIL_LOCK = root / ".mail.lock"
        core.PC_LOCK = root / ".pc.lock"
        core.HISTORY_LOCK = root / ".history.lock"

        core.SETTINGS_JSON = root / "settings.json"
        core.DATA_BACKUPS = root / "backups"

        core.migrate_mail_schema()
        core.ensure_pc_schema()
        core.ensure_history_schema()

    def tearDown(self):
        self.temp.cleanup()

    def future(self):
        return (
            dt.datetime.now()
            .replace(second=0, microsecond=0)
            + dt.timedelta(hours=2)
        )

    def test_channels(self):
        for channel in ("email", "pc", "both"):
            core.save_group(
                pair_id=None,
                channel=channel,
                subject=channel,
                body="test",
                run_at=self.future(),
                repeat="once",
                category="Genel",
            )

        self.assertEqual(
            sorted(
                item["channel"]
                for item in core.load_groups()
            ),
            ["both", "email", "pc"],
        )

    def test_search_category(self):
        core.save_group(
            pair_id=None,
            channel="email",
            subject="Elektrik faturası",
            body="Ödeme yap",
            run_at=self.future(),
            repeat="once",
            category="Ödeme",
        )

        result = core.search_groups(
            "elektrik",
            category="Ödeme",
        )

        self.assertEqual(
            len(result),
            1,
        )

    def test_duplicate(self):
        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="Test",
            body="Body",
            run_at=self.future(),
            repeat="daily",
            category="İş",
        )

        duplicate = core.duplicate_group(pair)

        self.assertNotEqual(
            pair,
            duplicate,
        )

        self.assertEqual(
            len(core.load_groups()),
            2,
        )

    def test_duplicate_subject_suffix_uses_runtime_language(self):
        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="Bericht",
            body="",
            run_at=self.future(),
            repeat="once",
        )

        with mock.patch.object(
            core.runtime_config,
            "load_settings",
            return_value={"language": "de"},
        ):
            duplicate = core.duplicate_group(pair)

        groups = {
            item["pair_id"]: item
            for item in core.load_groups()
        }
        self.assertEqual(
            groups[duplicate]["subject"],
            "Bericht — Kopie",
        )

    def test_snooze(self):
        pair = core.save_group(
            pair_id=None,
            channel="pc",
            subject="Test",
            body="Body",
            run_at=self.future(),
            repeat="once",
        )

        core.snooze_group(
            pair,
            10,
        )

        group = {
            item["pair_id"]: item
            for item in core.load_groups()
        }[pair]

        row = group["pc_row"]

        self.assertTrue(
            row["snooze_until"]
        )

    def test_both_mutations_rollback_when_second_write_fails(
        self,
    ):
        pair = core.save_group(
            pair_id=None,
            channel="both",
            subject="ROLLBACK TEST",
            body="BODY",
            run_at=self.future(),
            repeat="once",
        )

        operations = (
            (
                "delete",
                lambda: core.delete_group(
                    pair
                ),
            ),
            (
                "enable",
                lambda: core.set_group_enabled(
                    pair,
                    False,
                ),
            ),
            (
                "snooze",
                lambda: core.snooze_group(
                    pair,
                    15,
                ),
            ),
            (
                "complete",
                lambda: core.complete_group(
                    pair
                ),
            ),
        )

        real_atomic_write = (
            core.atomic_write
        )

        for name, operation in operations:
            with self.subTest(
                operation=name
            ):
                before_mail = (
                    core.MAIL_CSV
                    .read_bytes()
                )
                before_pc = (
                    core.PC_CSV
                    .read_bytes()
                )
                before_history = (
                    core.HISTORY_CSV
                    .read_bytes()
                )

                failed = False

                def fail_second_write(
                    path,
                    fields,
                    rows,
                ):
                    nonlocal failed

                    if (
                        path == core.PC_CSV
                        and not failed
                    ):
                        failed = True
                        raise OSError(
                            "injected second-write failure"
                        )

                    return real_atomic_write(
                        path,
                        fields,
                        rows,
                    )

                with (
                    mock.patch.object(
                        core,
                        "atomic_write",
                        side_effect=(
                            fail_second_write
                        ),
                    ),
                    self.assertRaises(
                        OSError
                    ),
                ):
                    operation()

                self.assertTrue(failed)

                self.assertEqual(
                    core.MAIL_CSV
                    .read_bytes(),
                    before_mail,
                )

                self.assertEqual(
                    core.PC_CSV
                    .read_bytes(),
                    before_pc,
                )

                self.assertEqual(
                    core.HISTORY_CSV
                    .read_bytes(),
                    before_history,
                )

    def test_month_end_anchor(self):
        jan31 = dt.datetime(
            2027,
            1,
            31,
            10,
            0,
        )

        feb = core.compute_next_run(
            jan31,
            "monthly",
            31,
        )

        self.assertEqual(
            feb,
            dt.datetime(
                2027,
                2,
                28,
                10,
                0,
            ),
        )

        march = core.compute_next_run(
            feb,
            "monthly",
            31,
        )

        self.assertEqual(
            march,
            dt.datetime(
                2027,
                3,
                31,
                10,
                0,
            ),
        )

    def test_catchup_jumps_future(self):
        scheduled = (
            dt.datetime.now()
            .replace(second=0, microsecond=0)
            - dt.timedelta(days=5)
        )

        nxt = core.next_future_run(
            scheduled,
            "daily",
            dt.datetime.now(),
        )

        self.assertGreater(
            nxt,
            dt.datetime.now(),
        )

    def test_quiet_overnight(self):
        settings = {
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }

        self.assertTrue(
            core.is_quiet_time(
                dt.datetime(
                    2026,
                    8,
                    20,
                    23,
                    0,
                ),
                settings,
            )
        )

        self.assertTrue(
            core.is_quiet_time(
                dt.datetime(
                    2026,
                    8,
                    20,
                    7,
                    30,
                ),
                settings,
            )
        )

        self.assertFalse(
            core.is_quiet_time(
                dt.datetime(
                    2026,
                    8,
                    20,
                    12,
                    0,
                ),
                settings,
            )
        )

    def test_initial_preferences_bridge_from_public_profile(
        self,
    ):
        with mock.patch.object(
            core.runtime_config,
            "load_settings",
            return_value={
                "default_channel":
                    "pc",

                "default_snooze_minutes":
                    25,

                "profile_name":
                    "Must not be duplicated",

                "smtp_host":
                    "private.example",
            },
        ):
            settings = core.load_settings()

        self.assertEqual(
            settings[
                "default_channel"
            ],
            "pc",
        )

        self.assertEqual(
            settings[
                "default_snooze_minutes"
            ],
            25,
        )

        self.assertNotIn(
            "profile_name",
            settings,
        )

        self.assertNotIn(
            "smtp_host",
            settings,
        )

    def test_settings_save_is_durable_private_and_non_destructive(
        self,
    ):
        core.SETTINGS_JSON.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        core.SETTINGS_JSON.write_text(
            json.dumps(
                {
                    "default_channel":
                        "both",

                    "future_setting":
                        {
                            "keep": True,
                        },
                }
            ),
            encoding="utf-8",
        )

        os.chmod(
            core.SETTINGS_JSON,
            0o644,
        )

        real_fsync = os.fsync

        with (
            mock.patch.object(
                core.runtime_config,
                "load_settings",
                return_value={
                    "default_channel":
                        "pc",
                },
            ),
            mock.patch.object(
                core.os,
                "fsync",
                wraps=real_fsync,
            ) as fsync,
        ):
            core.save_settings(
                {
                    "quiet_hours_enabled":
                        True,
                }
            )

        saved = json.loads(
            core.SETTINGS_JSON.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            saved[
                "default_channel"
            ],
            "both",
        )

        self.assertEqual(
            saved[
                "future_setting"
            ],
            {
                "keep": True,
            },
        )

        self.assertTrue(
            saved[
                "quiet_hours_enabled"
            ]
        )

        self.assertEqual(
            core.SETTINGS_JSON
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )

        self.assertGreaterEqual(
            fsync.call_count,
            2,
        )

        leftovers = list(
            core.SETTINGS_JSON
            .parent
            .glob(
                ".settings.json.*.tmp"
            )
        )

        self.assertEqual(
            leftovers,
            [],
        )

    def test_settings_load_hardens_legacy_mode_without_rewriting(
        self,
    ):
        payload = (
            '{"future_setting": "preserved"}\n'
        )

        core.SETTINGS_JSON.write_text(
            payload,
            encoding="utf-8",
        )

        os.chmod(
            core.SETTINGS_JSON,
            0o644,
        )

        with mock.patch.object(
            core.runtime_config,
            "load_settings",
            return_value={},
        ):
            settings = core.load_settings()

        self.assertEqual(
            settings[
                "future_setting"
            ],
            "preserved",
        )

        self.assertEqual(
            core.SETTINGS_JSON.read_text(
                encoding="utf-8"
            ),
            payload,
        )

        self.assertEqual(
            core.SETTINGS_JSON
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )

    def test_corrupt_settings_are_distinct_and_quarantined(
        self,
    ):
        corrupt = b'{"broken": [not-json]\n'

        core.SETTINGS_JSON.write_bytes(
            corrupt
        )
        os.chmod(
            core.SETTINGS_JSON,
            0o644,
        )

        with mock.patch.object(
            core.runtime_config,
            "load_settings",
            return_value={
                "default_channel": "pc",
            },
        ):
            settings = core.load_settings()

        self.assertEqual(
            settings[
                "default_channel"
            ],
            "pc",
        )

        self.assertEqual(
            core.settings_load_state(),
            core
            .SETTINGS_STATE_CORRUPT_QUARANTINED,
        )

        self.assertFalse(
            core.SETTINGS_JSON.exists()
        )

        quarantines = (
            core.settings_quarantine_files()
        )

        self.assertEqual(
            len(quarantines),
            1,
        )

        self.assertEqual(
            quarantines[0].read_bytes(),
            corrupt,
        )

        self.assertEqual(
            quarantines[0]
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )

    def test_missing_settings_are_not_reported_as_corrupt(
        self,
    ):
        settings = core.load_settings()

        self.assertIn(
            "default_channel",
            settings,
        )

        self.assertEqual(
            core.settings_load_state(),
            core.SETTINGS_STATE_MISSING,
        )

        self.assertEqual(
            core.settings_quarantine_files(),
            [],
        )

    def test_save_quarantines_corrupt_bytes_before_overwrite(
        self,
    ):
        corrupt = b"not-json-preserve-exactly\n"

        core.SETTINGS_JSON.write_bytes(
            corrupt
        )

        with mock.patch.object(
            core.runtime_config,
            "load_settings",
            return_value={},
        ):
            core.save_settings(
                {
                    "default_category":
                        "İş",
                }
            )

        quarantines = (
            core.settings_quarantine_files()
        )

        self.assertEqual(
            len(quarantines),
            1,
        )
        self.assertEqual(
            quarantines[0].read_bytes(),
            corrupt,
        )
        self.assertEqual(
            quarantines[0]
            .stat()
            .st_mode
            & 0o777,
            0o600,
        )

        saved = json.loads(
            core.SETTINGS_JSON.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            saved[
                "default_category"
            ],
            "İş",
        )

        self.assertEqual(
            core.settings_load_state(),
            core
            .SETTINGS_STATE_CORRUPT_QUARANTINED,
        )

    def test_failed_quarantine_never_overwrites_corrupt_file(
        self,
    ):
        corrupt = b"corrupt-and-protected\n"
        core.SETTINGS_JSON.write_bytes(
            corrupt
        )

        real_replace = os.replace

        def fail_quarantine(
            source,
            target,
        ):
            if (
                Path(source)
                == core.SETTINGS_JSON
                and ".corrupt-"
                in Path(target).name
            ):
                raise OSError(
                    "injected quarantine failure"
                )

            return real_replace(
                source,
                target,
            )

        with (
            mock.patch.object(
                core.os,
                "replace",
                side_effect=fail_quarantine,
            ),
            self.assertRaises(
                core.SettingsPersistenceError
            ),
        ):
            core.save_settings(
                {
                    "default_channel":
                        "pc",
                }
            )

        self.assertEqual(
            core.SETTINGS_JSON.read_bytes(),
            corrupt,
        )

        self.assertEqual(
            core.settings_load_state(),
            core
            .SETTINGS_STATE_CORRUPT_UNQUARANTINED,
        )


if __name__ == "__main__":
    unittest.main()
