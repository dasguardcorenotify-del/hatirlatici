#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

import core_v2 as core


class IntegrityError(RuntimeError):
    pass


def validate_reminder(
    path: Path,
    *,
    require_pc_extensions: bool = False,
) -> None:
    if not path.exists():
        return

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = list(
            reader.fieldnames or []
        )

        required = list(
            core.BASE_FIELDS
        )

        if require_pc_extensions:
            required += [
                "pair_id",
                "channel",
                "lease_until",
            ]

        missing = [
            field
            for field in required
            if field not in fields
        ]

        if missing:
            raise IntegrityError(
                "Eksik CSV alanları: "
                + ", ".join(missing)
            )

        rows = list(reader)

    seen_ids = set()

    valid_repeats = {
        "",
        "none",
        "once",
        "daily",
        "weekly",
        "monthly",
        "every 15m",
        "every 30m",
        "every 1h",
        "every 2h",
    }

    for index, row in enumerate(
        rows,
        start=2,
    ):
        rid = (
            row.get("id")
            or ""
        ).strip()

        if not rid:
            raise IntegrityError(
                f"Satır {index}: boş id."
            )

        if rid in seen_ids:
            raise IntegrityError(
                f"Satır {index}: yinelenen id={rid}"
            )

        seen_ids.add(rid)

        enabled = (
            row.get("enabled")
            or ""
        ).strip()

        if enabled not in {"0", "1"}:
            raise IntegrityError(
                f"Satır {index}: enabled geçersiz."
            )

        repeat = (
            row.get("repeat")
            or ""
        ).strip()

        if repeat not in valid_repeats:
            raise IntegrityError(
                f"Satır {index}: repeat geçersiz."
            )

        for field in (
            "next_run",
            "snooze_until",
            "last_sent",
            "lease_until",
        ):
            value = (
                row.get(field)
                or ""
            ).strip()

            if (
                value
                and core.parse_dt(value)
                is None
            ):
                raise IntegrityError(
                    f"Satır {index}: "
                    f"{field} geçersiz."
                )

        try:
            count = int(
                (
                    row.get("send_count")
                    or "0"
                ).strip()
            )
        except ValueError as exc:
            raise IntegrityError(
                f"Satır {index}: "
                "send_count geçersiz."
            ) from exc

        if count < 0:
            raise IntegrityError(
                f"Satır {index}: "
                "send_count negatif."
            )


def validate_history(
    path: Path,
) -> None:
    if not path.exists():
        return

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = list(
            reader.fieldnames or []
        )

        missing = [
            field
            for field in core.HISTORY_FIELDS
            if field not in fields
        ]

        if missing:
            raise IntegrityError(
                "History alanları eksik: "
                + ", ".join(missing)
            )

        rows = list(reader)

    seen = set()

    for index, row in enumerate(
        rows,
        start=2,
    ):
        event_id = (
            row.get("event_id")
            or ""
        ).strip()

        if not event_id:
            raise IntegrityError(
                f"History satır {index}: "
                "boş event_id."
            )

        if event_id in seen:
            raise IntegrityError(
                f"History satır {index}: "
                "yinelenen event_id."
            )

        seen.add(event_id)

        sent_at = (
            row.get("sent_at")
            or ""
        ).strip()

        if (
            sent_at
            and core.parse_dt(sent_at)
            is None
        ):
            raise IntegrityError(
                f"History satır {index}: "
                "sent_at geçersiz."
            )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 2

    kind = argv[0]
    path = Path(argv[1])

    try:
        if kind == "mail":
            validate_reminder(
                path,
                require_pc_extensions=False,
            )

        elif kind == "pc":
            validate_reminder(
                path,
                require_pc_extensions=True,
            )

        elif kind == "history":
            validate_history(path)

        else:
            return 2

    except Exception as exc:
        print(
            f"INTEGRITY_FAIL={exc}",
            file=sys.stderr,
        )
        return 20

    print("INTEGRITY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main(sys.argv[1:])
    )
