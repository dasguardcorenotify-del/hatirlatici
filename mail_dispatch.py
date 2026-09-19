#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass
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


import runtime_config  # noqa: E402
import smtp_transport  # noqa: E402
import core_v2 as core  # noqa: E402
import l10n  # noqa: E402


LEASE_MINUTES = 10

MAX_JOBS_PER_CYCLE = 5

MAIL_STATUS_PREFIX = "MAIL_STATUS_V1 "
MAIL_STATUS_MAX_BYTES = 256

MAIL_DISPATCH_OK = 0
MAIL_DISPATCH_SMTP_FAILURE = 20
MAIL_DISPATCH_INTERNAL_FAILURE = 21


@dataclass(
    frozen=True
)
class MailJob:
    pair_id: str
    scheduled_value: str
    lease_until: str
    subject: str
    body: str
    category: str


@dataclass(
    frozen=True
)
class DispatchResult:
    exit_code: int
    status: str
    code: str


def _safe_error_code(
    value: object,
) -> str:
    allowed = {
        item.value
        for item in (
            smtp_transport
            .MailErrorCode
        )
    }

    if isinstance(
        value,
        smtp_transport.MailErrorCode,
    ):
        candidate = value.value
    else:
        candidate = str(
            value or ""
        ).strip()

    if candidate not in allowed:
        return "generic"

    return candidate


def encode_status_line(
    result: DispatchResult,
) -> bytes:
    status = (
        "ok"
        if result.status == "ok"
        else "error"
    )

    code = (
        "ok"
        if status == "ok"
        else _safe_error_code(
            result.code
        )
    )

    payload = json.dumps(
        {
            "code": code,
            "status": status,
            "version": 1,
        },
        ensure_ascii=True,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    ).encode("ascii")

    line = (
        MAIL_STATUS_PREFIX.encode(
            "ascii"
        )
        + payload
        + b"\n"
    )

    if len(line) > MAIL_STATUS_MAX_BYTES:
        raise RuntimeError(
            "mail status frame exceeds contract"
        )

    return line


def _now() -> dt.datetime:
    # core_v2 CSV scheduling uses naive local wall-clock
    # datetimes. Keep dispatcher comparisons identical.
    return (
        dt.datetime.now()
        .replace(
            second=0,
            microsecond=0,
        )
    )


def _log(
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
            / "mail_dispatch.log"
        )

        with path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                dt.datetime.now()
                .isoformat()
                + " "
                + str(message)
                + "\n"
            )

    except OSError:
        pass


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


def due_exists(
    now: dt.datetime | None = None,
) -> bool:
    now = (
        now
        or _now()
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
            "mail_row"
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


def claim_due(
    *,
    now: dt.datetime | None = None,
) -> list[MailJob]:
    now = (
        now
        or _now()
    )

    settings = (
        core.load_settings()
    )

    language = l10n.normalize_language(
        runtime_config
        .load_settings()
        .get(
            "language",
            "en",
        )
    )

    default_subject = l10n.text(
        "reminder_default_title",
        language,
    )

    if core.is_quiet_time(
        now,
        settings,
    ):
        return []

    lease_until = (
        core.fmt_dt(
            now
            + dt.timedelta(
                minutes=(
                    LEASE_MINUTES
                )
            )
        )
    )

    jobs: list[
        MailJob
    ] = []

    with core.exclusive(
        core.MAIL_LOCK
    ):
        fields, rows = (
            core.read_csv(
                core.MAIL_CSV,
                core.FIELDS,
            )
        )

        changed = False

        for row in rows:
            if len(
                jobs
            ) >= MAX_JOBS_PER_CYCLE:
                break

            if not _row_due(
                row,
                now,
            ):
                continue

            pair_id = str(
                row.get(
                    "pair_id",
                    "",
                )
            ).strip()

            scheduled_value = str(
                row.get(
                    "next_run",
                    "",
                )
            ).strip()

            if (
                not pair_id
                or not scheduled_value
            ):
                continue

            row[
                "lease_until"
            ] = lease_until

            changed = True

            jobs.append(
                MailJob(
                    pair_id=pair_id,
                    scheduled_value=(
                        scheduled_value
                    ),
                    lease_until=(
                        lease_until
                    ),
                    subject=(
                        str(
                            row.get(
                                "subject",
                                "",
                            )
                            or default_subject
                        )
                    ),
                    body=str(
                        row.get(
                            "body",
                            "",
                        )
                        or ""
                    ),
                    category=str(
                        row.get(
                            "category",
                            "Genel",
                        )
                        or "Genel"
                    ),
                )
            )

        if changed:
            core.atomic_write(
                core.MAIL_CSV,
                core.ensure_fields(
                    fields
                ),
                rows,
            )

    return jobs


def release_lease(
    job: MailJob,
) -> bool:
    with core.exclusive(
        core.MAIL_LOCK
    ):
        fields, rows = (
            core.read_csv(
                core.MAIL_CSV,
                core.FIELDS,
            )
        )

        changed = False

        for row in rows:
            if (
                str(
                    row.get(
                        "pair_id",
                        "",
                    )
                ).strip()
                != job.pair_id
            ):
                continue

            if (
                str(
                    row.get(
                        "next_run",
                        "",
                    )
                ).strip()
                != job.scheduled_value
            ):
                continue

            if (
                str(
                    row.get(
                        "lease_until",
                        "",
                    )
                ).strip()
                != job.lease_until
            ):
                continue

            row[
                "lease_until"
            ] = ""

            changed = True

            break

        if changed:
            core.atomic_write(
                core.MAIL_CSV,
                core.ensure_fields(
                    fields
                ),
                rows,
            )

        return changed


def finalize_success(
    job: MailJob,
    *,
    sent_at: dt.datetime | None = None,
) -> bool:
    sent_at = (
        sent_at
        or _now()
    )

    history = None

    with core.exclusive(
        core.MAIL_LOCK
    ):
        fields, rows = (
            core.read_csv(
                core.MAIL_CSV,
                core.FIELDS,
            )
        )

        target = None

        for row in rows:
            if (
                str(
                    row.get(
                        "pair_id",
                        "",
                    )
                ).strip()
                != job.pair_id
            ):
                continue

            if (
                str(
                    row.get(
                        "next_run",
                        "",
                    )
                ).strip()
                != job.scheduled_value
            ):
                continue

            if (
                str(
                    row.get(
                        "lease_until",
                        "",
                    )
                ).strip()
                != job.lease_until
            ):
                continue

            target = row
            break

        if target is None:
            return False

        scheduled = (
            core.parse_dt(
                job.scheduled_value
            )
        )

        if scheduled is None:
            target[
                "lease_until"
            ] = ""

            core.atomic_write(
                core.MAIL_CSV,
                core.ensure_fields(
                    fields
                ),
                rows,
            )

            return False

        try:
            count = int(
                str(
                    target.get(
                        "send_count",
                        "0",
                    )
                    or "0"
                ).strip()
            )

        except ValueError:
            count = 0

        repeat = str(
            target.get(
                "repeat",
                "once",
            )
            or "once"
        ).strip()

        try:
            anchor_day = int(
                str(
                    target.get(
                        "anchor_day",
                        scheduled.day,
                    )
                    or scheduled.day
                ).strip()
            )

        except (
            TypeError,
            ValueError,
        ):
            anchor_day = (
                scheduled.day
            )

        target[
            "last_sent"
        ] = core.fmt_dt(
            sent_at
        )

        target[
            "send_count"
        ] = str(
            count + 1
        )

        target[
            "updated_at"
        ] = core.fmt_dt(
            sent_at
        )

        next_run = (
            core.next_future_run(
                scheduled,
                repeat,
                sent_at,
                anchor_day,
            )
        )

        if next_run is None:
            target[
                "enabled"
            ] = "0"

            target[
                "next_run"
            ] = ""

        else:
            target[
                "enabled"
            ] = "1"

            target[
                "next_run"
            ] = core.fmt_dt(
                next_run
            )

        target[
            "lease_until"
        ] = ""

        target[
            "snooze_until"
        ] = ""

        core.snapshot_file(
            core.MAIL_CSV,
            "mail_runtime",
        )

        core.atomic_write(
            core.MAIL_CSV,
            core.ensure_fields(
                fields
            ),
            rows,
        )

        history = {
            "pair_id":
                job.pair_id,

            "channel":
                "email",

            "sent_at":
                core.fmt_dt(
                    sent_at
                ),

            "subject":
                job.subject,

            "body":
                job.body,

            "category":
                job.category,

            "action":
                "sent",
        }

    if history:
        core.append_history(
            **history
        )

    return True


def _dispatch() -> DispatchResult:
    runtime_config.ensure_runtime_dirs()

    core.migrate_mail_schema()
    core.ensure_history_schema()

    jobs = claim_due()

    if not jobs:
        return DispatchResult(
            exit_code=MAIL_DISPATCH_OK,
            status="ok",
            code="ok",
        )

    failures = 0
    first_error_code = None

    for job in jobs:
        try:
            smtp_transport.send_reminder(
                subject=(
                    job.subject
                ),
                body=(
                    job.body
                ),
                pair_id=(
                    job.pair_id
                ),
                scheduled_value=(
                    job.scheduled_value
                ),
            )

        except (
            smtp_transport
            .MailTransportError
        ) as exc:
            release_lease(
                job
            )

            failures += 1

            error_code = (
                _safe_error_code(
                    getattr(
                        exc,
                        "code",
                        "generic",
                    )
                )
            )

            if first_error_code is None:
                first_error_code = (
                    error_code
                )

            _log(
                "SMTP_FAIL "
                f"code={error_code}"
            )

            continue

        finalized = (
            finalize_success(
                job
            )
        )

        if not finalized:
            # SMTP sunucusu mesajı kabul etmiş olabilir,
            # ancak yerel occurrence kullanıcı tarafından
            # eşzamanlı değiştirilmiş olabilir. Burada
            # otomatik tekrar gönderim yapmıyoruz.
            _log(
                "SMTP_SENT_STATE_STALE"
            )

        else:
            _log(
                "SMTP_SENT"
            )

    if failures:
        return DispatchResult(
            exit_code=(
                MAIL_DISPATCH_SMTP_FAILURE
            ),
            status="error",
            code=(
                first_error_code
                or "generic"
            ),
        )

    return DispatchResult(
        exit_code=MAIL_DISPATCH_OK,
        status="ok",
        code="ok",
    )


def run() -> int:
    return _dispatch().exit_code


def main() -> int:
    try:
        result = _dispatch()
    except Exception:
        # The scheduler receives a stable safe failure frame. Normal users
        # never see a Python traceback or exception/server response here.
        result = DispatchResult(
            exit_code=(
                MAIL_DISPATCH_INTERNAL_FAILURE
            ),
            status="error",
            code="generic",
        )

    try:
        sys.stdout.buffer.write(
            encode_status_line(
                result
            )
        )
        sys.stdout.buffer.flush()
    except Exception:
        return MAIL_DISPATCH_INTERNAL_FAILURE

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
