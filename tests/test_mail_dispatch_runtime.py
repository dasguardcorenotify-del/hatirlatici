import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


class MailDispatchRuntimeTests(
    unittest.TestCase
):
    def run_case(
        self,
        code: str,
    ):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)

            env = (
                os.environ.copy()
            )

            env.update(
                {
                    "XDG_CONFIG_HOME":
                        str(
                            base
                            / "config"
                        ),

                    "XDG_DATA_HOME":
                        str(
                            base
                            / "data"
                        ),

                    "XDG_STATE_HOME":
                        str(
                            base
                            / "state"
                        ),

                    "PYTHONPATH":
                        os.pathsep.join(
                            [
                                str(ROOT),
                                str(
                                    ROOT
                                    / "ui_v2"
                                ),
                            ]
                        ),
                }
            )

            return subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code,
                ],
                env=env,
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_success_finalizes_once(self):
        code = r'''
import datetime as dt

import runtime_config
import core_v2 as core
import mail_dispatch
import smtp_transport


runtime_config.ensure_runtime_dirs()

core.migrate_mail_schema()
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
    channel="email",
    subject="MAIL TEST",
    body="BODY",
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

with core.exclusive(core.MAIL_LOCK):
    fields, rows = core.read_csv(
        core.MAIL_CSV,
        core.FIELDS,
    )

    for row in rows:
        if row.get("pair_id") == pair:
            row["next_run"] = core.fmt_dt(due)

    core.atomic_write(
        core.MAIL_CSV,
        core.ensure_fields(fields),
        rows,
    )


calls = []

def fake_send(**kwargs):
    calls.append(kwargs)


smtp_transport.send_reminder = fake_send

rc = mail_dispatch.run()

assert rc == 0
assert len(calls) == 1

groups = {
    str(item["pair_id"]): item
    for item in core.load_groups()
}

row = groups[pair]["mail_row"]

assert row["send_count"] == "1"
assert row["enabled"] == "0"
assert not row["lease_until"]

history = [
    item
    for item in core.load_history()
    if item.get("pair_id") == pair
    and item.get("channel") == "email"
]

assert len(history) == 1
assert history[0]["action"] == "sent"

# İkinci cycle yeniden göndermemeli.
rc = mail_dispatch.run()

assert rc == 0
assert len(calls) == 1

print("MAIL_DISPATCH_SUCCESS=PASS")
print("MAIL_DISPATCH_NO_SECOND_SEND=PASS")
print("MAIL_HISTORY_ONCE=PASS")
'''

        result = self.run_case(
            code
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                result.stdout
                + "\n"
                + result.stderr
            ),
        )

        self.assertIn(
            "MAIL_HISTORY_ONCE=PASS",
            result.stdout,
        )

    def test_failure_releases_lease(self):
        code = r'''
import datetime as dt

import runtime_config
import core_v2 as core
import mail_dispatch
import smtp_transport


runtime_config.ensure_runtime_dirs()

core.migrate_mail_schema()
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
    channel="email",
    subject="FAIL TEST",
    body="BODY",
    run_at=future,
    repeat="once",
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

with core.exclusive(core.MAIL_LOCK):
    fields, rows = core.read_csv(
        core.MAIL_CSV,
        core.FIELDS,
    )

    for row in rows:
        if row.get("pair_id") == pair:
            row["next_run"] = core.fmt_dt(due)

    core.atomic_write(
        core.MAIL_CSV,
        core.ensure_fields(fields),
        rows,
    )


def fail_send(**kwargs):
    raise smtp_transport.MailTransportError(
        "fake failure"
    )


smtp_transport.send_reminder = fail_send

rc = mail_dispatch.run()

assert rc == 20

groups = {
    str(item["pair_id"]): item
    for item in core.load_groups()
}

row = groups[pair]["mail_row"]

assert row["send_count"] == "0"
assert row["enabled"] == "1"
assert not row["lease_until"]

history = [
    item
    for item in core.load_history()
    if item.get("pair_id") == pair
    and item.get("channel") == "email"
]

assert history == []

print("MAIL_FAILURE_LEASE_RELEASE=PASS")
print("MAIL_FAILURE_HISTORY=NONE")
'''

        result = self.run_case(
            code
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                result.stdout
                + "\n"
                + result.stderr
            ),
        )

        self.assertIn(
            "MAIL_FAILURE_LEASE_RELEASE=PASS",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
