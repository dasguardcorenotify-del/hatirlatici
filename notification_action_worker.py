#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

UI = ROOT / "ui_v2"

sys.path.insert(
    0,
    str(ROOT),
)

sys.path.insert(
    0,
    str(UI),
)

import runtime_config  # noqa: E402
import portal_notifications  # noqa: E402
import l10n  # noqa: E402
import notification_ipc  # noqa: E402
import core_v2 as core  # noqa: E402


LOG_DIR = (
    runtime_config
    .logs_dir()
)

LOG_FILE = (
    LOG_DIR
    / "notification_worker.log"
)


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


def _snooze_minutes(
    value: object,
) -> int:
    try:
        minutes = int(value)
    except (
        TypeError,
        ValueError,
    ):
        minutes = 10

    return max(
        1,
        min(
            minutes,
            1440,
        ),
    )


def log(
    message: str,
) -> None:
    try:
        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )

        with LOG_FILE.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                f"{dt.datetime.now().isoformat()} "
                f"{message}\n"
            )

    except OSError:
        pass


def show_notification(
    notification_id: str,
    subject: str,
    body: str,
    *,
    language: str | None = None,
    snooze_minutes: int = 10,
) -> tuple[bool, str]:
    try:
        action = (
            portal_notifications
            .notify_and_wait(
                notification_id,
                subject,
                body or subject,
                timeout_seconds=36,
                language=language,
                snooze_minutes=(
                    snooze_minutes
                ),
            )
        )

    except (
        portal_notifications
        .PortalNotificationError
    ) as error:
        log(
            "PORTAL_DELIVERY_FAIL "
            + "type="
            + type(error).__name__
        )

        return False, ""

    if action == "complete":
        return True, "complete"

    if action == "snooze":
        return True, "snooze"

    # Portal accepted the notification but the bounded
    # interaction window ended without an action.
    return True, "sent"


def release_lease(
    pair_id: str,
    scheduled_value: str,
    lease_until: str,
) -> None:
    with core.exclusive(
        core.PC_LOCK
    ):
        fields, rows = core.read_csv(
            core.PC_CSV,
            core.FIELDS,
        )

        changed = False

        for row in rows:
            if (
                row.get("pair_id")
                or ""
            ).strip() != pair_id:
                continue

            if (
                row.get("next_run")
                or ""
            ).strip() != scheduled_value:
                continue

            if (
                row.get("lease_until")
                or ""
            ).strip() != lease_until:
                continue

            row["lease_until"] = ""
            changed = True

        if changed:
            core.atomic_write(
                core.PC_CSV,
                core.ensure_fields(
                    fields
                ),
                rows,
            )


def finalize_delivery(
    pair_id: str,
    scheduled_value: str,
    lease_until: str,
    action: str,
    *,
    now: dt.datetime | None = None,
    snooze_minutes: int | None = None,
) -> bool:
    now = (
        now
        or dt.datetime.now()
    ).replace(
        second=0,
        microsecond=0,
    )

    history_payload = None
    default_title = l10n.text(
        "reminder_default_title",
        _runtime_language(),
    )

    with core.exclusive(
        core.PC_LOCK
    ):
        fields, rows = core.read_csv(
            core.PC_CSV,
            core.FIELDS,
        )

        fields = core.ensure_fields(
            fields
        )

        target = None

        for row in rows:
            if (
                row.get("pair_id")
                or ""
            ).strip() != pair_id:
                continue

            if (
                row.get("next_run")
                or ""
            ).strip() != scheduled_value:
                continue

            if (
                row.get("lease_until")
                or ""
            ).strip() != lease_until:
                continue

            target = row
            break

        # Stale callbacks are fail-closed.
        if target is None:
            return False

        try:
            send_count = int(
                (
                    target.get(
                        "send_count"
                    )
                    or "0"
                ).strip()
            )

        except ValueError:
            send_count = 0

        target["last_sent"] = (
            core.fmt_dt(now)
        )

        target["send_count"] = str(
            send_count + 1
        )

        target["updated_at"] = (
            core.fmt_dt(now)
        )

        scheduled = core.parse_dt(
            scheduled_value
        )

        if scheduled is None:
            return False

        repeat = (
            target.get("repeat")
            or "once"
        ).strip()

        try:
            anchor_day = int(
                (
                    target.get(
                        "anchor_day"
                    )
                    or str(
                        scheduled.day
                    )
                ).strip()
            )

        except ValueError:
            anchor_day = (
                scheduled.day
            )

        if action == "snooze":
            if snooze_minutes is None:
                settings = (
                    core.load_settings()
                )

                minutes = _snooze_minutes(
                    settings.get(
                        "default_snooze_minutes",
                        10,
                    )
                )
            else:
                minutes = _snooze_minutes(
                    snooze_minutes
                )

            target["enabled"] = "1"
            target["lease_until"] = ""

            target["snooze_until"] = (
                core.fmt_dt(
                    now
                    + dt.timedelta(
                        minutes=minutes
                    )
                )
            )

            history_action = (
                "snoozed"
            )

        else:
            nxt = core.next_future_run(
                scheduled,
                repeat,
                now,
                anchor_day,
            )

            if nxt is None:
                target["enabled"] = "0"
                target["next_run"] = ""

            else:
                target["enabled"] = "1"

                target["next_run"] = (
                    core.fmt_dt(nxt)
                )

            target["lease_until"] = ""
            target["snooze_until"] = ""

            history_action = (
                "completed"
                if action
                == "complete"
                else "sent"
            )

        core.snapshot_file(
            core.PC_CSV,
            "pc_runtime",
        )

        core.atomic_write(
            core.PC_CSV,
            fields,
            rows,
        )

        history_payload = {
            "pair_id": pair_id,
            "channel": "pc",
            "sent_at":
                core.fmt_dt(now),

            "subject":
                target.get(
                    "subject"
                )
                or default_title,

            "body":
                target.get(
                    "body"
                )
                or "",

            "category":
                target.get(
                    "category"
                )
                or "Genel",

            "action":
                history_action,
        }

    if history_payload:
        core.append_history(
            **history_payload
        )

    return True


def main(
    argv: list[str],
) -> int:
    if len(argv) != 3:
        return 2

    (
        pair_id,
        scheduled_value,
        lease_until,
    ) = argv

    runtime_config.ensure_runtime_dirs()

    language = _runtime_language()

    notification_settings = (
        core.load_settings()
    )

    snooze_minutes = _snooze_minutes(
        notification_settings.get(
            "default_snooze_minutes",
            10,
        )
    )

    try:
        subject, body, worker_token = (
            notification_ipc
            .read_payload(
                sys.stdin.buffer
            )
        )
    except (
        notification_ipc
        .NotificationPayloadError,
        OSError,
    ):
        release_lease(
            pair_id,
            scheduled_value,
            lease_until,
        )

        log(
            "PAYLOAD_FAIL "
            "transport=anonymous-pipe"
        )

        return 3

    notification_id = (
        "reminder-"
        + portal_notifications
        .sanitize_id(
            pair_id
        )
        + "-"
        + portal_notifications
        .sanitize_id(
            worker_token
        )
    )

    log(
        "START "
        f"pair={pair_id} "
        f"transport=portal"
    )

    delivered, action = (
        show_notification(
            notification_id,
            subject,
            body,
            language=language,
            snooze_minutes=(
                snooze_minutes
            ),
        )
    )

    if not delivered:
        release_lease(
            pair_id,
            scheduled_value,
            lease_until,
        )

        log(
            "DELIVERY_FAIL "
            "transport=portal"
        )

        return 10

    updated = finalize_delivery(
        pair_id,
        scheduled_value,
        lease_until,
        action,
        snooze_minutes=(
            snooze_minutes
        ),
    )

    log(
        "DONE "
        f"action={action} "
        f"updated={updated} "
        "transport=portal"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(
            sys.argv[1:]
        )
    )
