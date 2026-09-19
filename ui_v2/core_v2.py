#!/usr/bin/env python3
from __future__ import annotations

import calendar
import csv
import datetime as dt
import fcntl
import json
import os
import shutil
import stat
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

import runtime_config
import l10n
from typing import Dict, Iterator, List, Optional, Tuple


ROOT = runtime_config.data_dir()

MAIL_CSV = runtime_config.mail_csv_path()
PC_CSV = runtime_config.pc_csv_path()
HISTORY_CSV = runtime_config.history_path()

MAIL_LOCK = runtime_config.mail_lock_path()
PC_LOCK = runtime_config.pc_lock_path()
HISTORY_LOCK = runtime_config.history_lock_path()

SETTINGS_JSON = runtime_config.app_settings_path()
DATA_BACKUPS = runtime_config.data_backups_dir()

TIME_FMT = "%Y-%m-%d %H:%M"

BASE_FIELDS = [
    "id",
    "enabled",
    "next_run",
    "repeat",
    "snooze_until",
    "last_sent",
    "send_count",
    "subject",
    "body",
]

EXTRA_FIELDS = [
    "pair_id",
    "channel",
    "category",
    "anchor_day",
    "created_at",
    "updated_at",
    "lease_until",
]

FIELDS = BASE_FIELDS + EXTRA_FIELDS

HISTORY_FIELDS = [
    "event_id",
    "pair_id",
    "channel",
    "sent_at",
    "subject",
    "body",
    "category",
    "action",
]

CATEGORIES = [
    "Genel",
    "Kişisel",
    "İş",
    "Ödeme",
    "Sağlık",
    "Alışveriş",
    "Diğer",
]

REPEAT_VALUE_BY_LABEL = {
    "Tek seferlik": "once",
    "Her gün": "daily",
    "Her hafta": "weekly",
    "Her ay": "monthly",
    "Her 15 dakika": "every 15m",
    "Her 30 dakika": "every 30m",
    "Her 1 saat": "every 1h",
    "Her 2 saat": "every 2h",
}

REPEAT_LABEL_BY_VALUE = {
    value: label
    for label, value in REPEAT_VALUE_BY_LABEL.items()
}

DEFAULT_SETTINGS: Dict[str, object] = {
    "default_channel": "email",
    "default_category": "Genel",
    "default_snooze_minutes": 10,
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "notification_timeout_ms": 30000,
    "minimize_to_tray": True,
}


def _localized_core_text(key: str) -> str:
    try:
        language = l10n.normalize_language(
            runtime_config
            .load_settings()
            .get(
                "language",
                "en",
            )
        )
    except Exception:
        language = "en"

    return l10n.text(
        key,
        language,
    )


@contextmanager
def exclusive(path: Path) -> Iterator[None]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_CLOEXEC
        | os.O_NOFOLLOW
    )
    directory_fd = os.open(
        path.parent,
        directory_flags,
    )

    descriptor = None

    try:
        os.fchmod(
            directory_fd,
            0o700,
        )
        descriptor = os.open(
            path.name,
            (
                os.O_RDWR
                | os.O_CREAT
                | os.O_CLOEXEC
                | os.O_NOFOLLOW
            ),
            0o600,
            dir_fd=directory_fd,
        )
        metadata = os.fstat(
            descriptor
        )

        if not stat.S_ISREG(
            metadata.st_mode
        ):
            raise OSError(
                "Lock path is not a regular file"
            )

        if metadata.st_nlink != 1:
            raise OSError(
                "Lock file has an unsafe hard-link count"
            )

        os.fchmod(
            descriptor,
            0o600,
        )
        fcntl.flock(
            descriptor,
            fcntl.LOCK_EX,
        )

        try:
            yield
        finally:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_UN,
            )
    finally:
        if descriptor is not None:
            os.close(
                descriptor
            )
        os.close(
            directory_fd
        )


def parse_dt(value: str) -> Optional[dt.datetime]:
    value = (value or "").strip()

    if not value:
        return None

    try:
        return dt.datetime.strptime(
            value,
            TIME_FMT,
        )
    except ValueError:
        return None


def fmt_dt(value: Optional[dt.datetime]) -> str:
    if value is None:
        return ""

    return value.strftime(TIME_FMT)


def _now_string() -> str:
    return fmt_dt(
        dt.datetime.now().replace(
            second=0,
            microsecond=0,
        )
    )


def read_csv(
    path: Path,
    default_fields: List[str],
) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        return list(default_fields), []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        fields = list(
            reader.fieldnames
            or default_fields
        )

        rows = list(reader)

    return fields, rows


def atomic_write(
    path: Path,
    fields: List[str],
    rows: List[Dict[str, str]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_name = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_name = temp.name

            writer = csv.DictWriter(
                temp,
                fieldnames=fields,
                extrasaction="ignore",
            )

            writer.writeheader()

            for row in rows:
                writer.writerow(
                    {
                        field: row.get(field, "")
                        for field in fields
                    }
                )

            temp.flush()
            os.fsync(temp.fileno())

        os.replace(
            temp_name,
            path,
        )

        directory_fd = os.open(
            str(path.parent),
            os.O_DIRECTORY,
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if (
            temp_name
            and os.path.exists(temp_name)
        ):
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def _atomic_write_group_pair(
    *,
    mail_fields: List[str],
    mail_rows: List[Dict[str, str]],
    pc_fields: List[str],
    pc_rows: List[Dict[str, str]],
    old_mail_rows: List[Dict[str, str]],
    old_pc_rows: List[Dict[str, str]],
) -> None:
    """Commit the two channel files or restore both pre-images."""
    try:
        atomic_write(
            MAIL_CSV,
            mail_fields,
            mail_rows,
        )

        atomic_write(
            PC_CSV,
            pc_fields,
            pc_rows,
        )

    except Exception:
        # Attempt each rollback independently.  A failure restoring one
        # file must not prevent the other pre-image from being restored.
        for path, fields, rows in (
            (
                MAIL_CSV,
                mail_fields,
                old_mail_rows,
            ),
            (
                PC_CSV,
                pc_fields,
                old_pc_rows,
            ),
        ):
            try:
                atomic_write(
                    path,
                    fields,
                    rows,
                )
            except Exception:
                pass

        raise


def snapshot_file(
    path: Path,
    group: str,
    keep: int = 20,
) -> Optional[Path]:
    if not path.exists():
        return None

    target_dir = (
        DATA_BACKUPS
        / group
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = dt.datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    target = (
        target_dir
        / f"{path.stem}_{stamp}{path.suffix}"
    )

    shutil.copy2(
        path,
        target,
    )

    files = sorted(
        target_dir.glob(
            f"{path.stem}_*{path.suffix}"
        ),
        key=lambda item:
        item.stat().st_mtime,
        reverse=True,
    )

    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass

    return target


def ensure_fields(
    fields: List[str],
) -> List[str]:
    result = list(fields)

    for field in FIELDS:
        if field not in result:
            result.append(field)

    return result


def next_id(
    rows: List[Dict[str, str]],
) -> int:
    highest = 0

    for row in rows:
        try:
            highest = max(
                highest,
                int(
                    (
                        row.get("id")
                        or "0"
                    ).strip()
                ),
            )
        except ValueError:
            pass

    return highest + 1


def _anchor_from_row(
    row: Dict[str, str],
) -> int:
    try:
        value = int(
            (
                row.get("anchor_day")
                or ""
            ).strip()
        )

        if 1 <= value <= 31:
            return value

    except ValueError:
        pass

    run_at = parse_dt(
        row.get("next_run", "")
    )

    if run_at is not None:
        return run_at.day

    return 1


def migrate_mail_schema() -> None:
    with exclusive(MAIL_LOCK):
        fields, rows = read_csv(
            MAIL_CSV,
            BASE_FIELDS,
        )

        fields = ensure_fields(fields)

        changed = False
        now = _now_string()

        for row in rows:
            rid = (
                row.get("id")
                or ""
            ).strip() or uuid.uuid4().hex[:8]

            defaults = {
                "pair_id": f"mail-{rid}",
                "channel": "email",
                "category": "Genel",
                "anchor_day": str(
                    _anchor_from_row(row)
                ),
                "created_at": now,
                "updated_at": now,
            }

            for key, value in defaults.items():
                if not (
                    row.get(key)
                    or ""
                ).strip():
                    row[key] = value
                    changed = True

        if changed or not MAIL_CSV.exists():
            snapshot_file(
                MAIL_CSV,
                "schema",
            )

            atomic_write(
                MAIL_CSV,
                fields,
                rows,
            )


def ensure_pc_schema() -> None:
    with exclusive(PC_LOCK):
        fields, rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        fields = ensure_fields(fields)

        changed = False
        now = _now_string()

        for row in rows:
            rid = (
                row.get("id")
                or ""
            ).strip() or uuid.uuid4().hex[:8]

            defaults = {
                "pair_id": f"pc-{rid}",
                "channel": "pc",
                "category": "Genel",
                "anchor_day": str(
                    _anchor_from_row(row)
                ),
                "created_at": now,
                "updated_at": now,
            }

            for key, value in defaults.items():
                if not (
                    row.get(key)
                    or ""
                ).strip():
                    row[key] = value
                    changed = True

        if changed or not PC_CSV.exists():
            snapshot_file(
                PC_CSV,
                "schema",
            )

            atomic_write(
                PC_CSV,
                fields,
                rows,
            )


def ensure_history_schema() -> None:
    with exclusive(HISTORY_LOCK):
        fields, rows = read_csv(
            HISTORY_CSV,
            HISTORY_FIELDS,
        )

        changed = False

        for field in HISTORY_FIELDS:
            if field not in fields:
                fields.append(field)
                changed = True

        if changed or not HISTORY_CSV.exists():
            snapshot_file(
                HISTORY_CSV,
                "schema",
            )

            atomic_write(
                HISTORY_CSV,
                fields,
                rows,
            )


def _find_by_pair(
    rows: List[Dict[str, str]],
    pair_id: str,
) -> Optional[Dict[str, str]]:
    for row in rows:
        if (
            row.get("pair_id")
            or ""
        ).strip() == pair_id:
            return row

    return None


def _new_or_updated_row(
    *,
    fields: List[str],
    existing: Optional[Dict[str, str]],
    rows: List[Dict[str, str]],
    pair_id: str,
    selected_channel: str,
    subject: str,
    body: str,
    run_at: dt.datetime,
    repeat: str,
    category: str,
) -> Dict[str, str]:
    now = _now_string()

    if existing is None:
        row = {
            field: ""
            for field in fields
        }

        row["id"] = str(
            next_id(rows)
        )

        row["send_count"] = "0"
        row["last_sent"] = ""
        row["created_at"] = now

    else:
        row = {
            field:
            existing.get(field, "")
            for field in fields
        }

        if not row.get("created_at"):
            row["created_at"] = now

    row.update(
        {
            "enabled": "1",
            "next_run": fmt_dt(run_at),
            "repeat": repeat,
            "snooze_until": "",
            "subject": subject,
            "body": body or subject,
            "pair_id": pair_id,
            "channel": selected_channel,
            "category": category,
            "anchor_day": str(run_at.day),
            "updated_at": now,
        }
    )

    return row


def save_group(
    *,
    pair_id: Optional[str],
    channel: str,
    subject: str,
    body: str,
    run_at: dt.datetime,
    repeat: str,
    category: str = "Genel",
) -> str:
    channel = channel.strip().lower()
    subject = subject.strip()
    body = body.strip()
    category = (
        category.strip()
        or "Genel"
    )

    if channel not in {
        "email",
        "pc",
        "both",
    }:
        raise ValueError(
            "Geçersiz hatırlatma yöntemi."
        )

    if not subject:
        raise ValueError(
            "Hatırlatma başlığı boş olamaz."
        )

    if category not in CATEGORIES:
        raise ValueError(
            "Geçersiz kategori."
        )

    now = dt.datetime.now().replace(
        second=0,
        microsecond=0,
    )

    if run_at <= now:
        raise ValueError(
            "Hatırlatma zamanı gelecekte olmalı."
        )

    if repeat not in REPEAT_LABEL_BY_VALUE:
        raise ValueError(
            "Geçersiz tekrar seçeneği."
        )

    pair_id = (
        pair_id
        or uuid.uuid4().hex
    )

    with exclusive(MAIL_LOCK), exclusive(PC_LOCK):
        mail_fields, mail_rows = read_csv(
            MAIL_CSV,
            FIELDS,
        )

        pc_fields, pc_rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        mail_fields = ensure_fields(
            mail_fields
        )

        pc_fields = ensure_fields(
            pc_fields
        )

        old_mail = [
            dict(row)
            for row in mail_rows
        ]

        old_pc = [
            dict(row)
            for row in pc_rows
        ]

        existing_mail = _find_by_pair(
            mail_rows,
            pair_id,
        )

        existing_pc = _find_by_pair(
            pc_rows,
            pair_id,
        )

        if channel in {
            "email",
            "both",
        }:
            updated = _new_or_updated_row(
                fields=mail_fields,
                existing=existing_mail,
                rows=mail_rows,
                pair_id=pair_id,
                selected_channel=channel,
                subject=subject,
                body=body,
                run_at=run_at,
                repeat=repeat,
                category=category,
            )

            mail_rows = [
                row
                for row in mail_rows
                if (
                    row.get("pair_id")
                    or ""
                ).strip() != pair_id
            ]

            mail_rows.append(updated)

        else:
            mail_rows = [
                row
                for row in mail_rows
                if (
                    row.get("pair_id")
                    or ""
                ).strip() != pair_id
            ]

        if channel in {
            "pc",
            "both",
        }:
            updated = _new_or_updated_row(
                fields=pc_fields,
                existing=existing_pc,
                rows=pc_rows,
                pair_id=pair_id,
                selected_channel=channel,
                subject=subject,
                body=body,
                run_at=run_at,
                repeat=repeat,
                category=category,
            )

            pc_rows = [
                row
                for row in pc_rows
                if (
                    row.get("pair_id")
                    or ""
                ).strip() != pair_id
            ]

            pc_rows.append(updated)

        else:
            pc_rows = [
                row
                for row in pc_rows
                if (
                    row.get("pair_id")
                    or ""
                ).strip() != pair_id
            ]

        snapshot_file(
            MAIL_CSV,
            "user_write",
        )

        snapshot_file(
            PC_CSV,
            "user_write",
        )

        try:
            atomic_write(
                PC_CSV,
                pc_fields,
                pc_rows,
            )

            atomic_write(
                MAIL_CSV,
                mail_fields,
                mail_rows,
            )

        except Exception:
            try:
                atomic_write(
                    PC_CSV,
                    pc_fields,
                    old_pc,
                )

                atomic_write(
                    MAIL_CSV,
                    mail_fields,
                    old_mail,
                )

            except Exception:
                pass

            raise

    return pair_id


def delete_group(
    pair_id: str,
) -> None:
    with exclusive(MAIL_LOCK), exclusive(PC_LOCK):
        mail_fields, mail_rows = read_csv(
            MAIL_CSV,
            FIELDS,
        )

        pc_fields, pc_rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        mail_fields = ensure_fields(
            mail_fields
        )

        pc_fields = ensure_fields(
            pc_fields
        )

        old_mail_rows = [
            dict(row)
            for row in mail_rows
        ]

        old_pc_rows = [
            dict(row)
            for row in pc_rows
        ]

        snapshot_file(
            MAIL_CSV,
            "user_write",
        )

        snapshot_file(
            PC_CSV,
            "user_write",
        )

        mail_rows = [
            row
            for row in mail_rows
            if (
                row.get("pair_id")
                or ""
            ).strip() != pair_id
        ]

        pc_rows = [
            row
            for row in pc_rows
            if (
                row.get("pair_id")
                or ""
            ).strip() != pair_id
        ]

        _atomic_write_group_pair(
            mail_fields=mail_fields,
            mail_rows=mail_rows,
            pc_fields=pc_fields,
            pc_rows=pc_rows,
            old_mail_rows=(
                old_mail_rows
            ),
            old_pc_rows=(
                old_pc_rows
            ),
        )


def set_group_enabled(
    pair_id: str,
    enabled: bool,
) -> None:
    value = (
        "1"
        if enabled
        else "0"
    )

    now = _now_string()

    with exclusive(MAIL_LOCK), exclusive(PC_LOCK):
        mail_fields, mail_rows = read_csv(
            MAIL_CSV,
            FIELDS,
        )

        pc_fields, pc_rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        mail_fields = ensure_fields(
            mail_fields
        )

        pc_fields = ensure_fields(
            pc_fields
        )

        old_mail_rows = [
            dict(row)
            for row in mail_rows
        ]

        old_pc_rows = [
            dict(row)
            for row in pc_rows
        ]

        for row in mail_rows:
            if (
                row.get("pair_id")
                or ""
            ).strip() == pair_id:
                row["enabled"] = value
                row["updated_at"] = now

        for row in pc_rows:
            if (
                row.get("pair_id")
                or ""
            ).strip() == pair_id:
                row["enabled"] = value
                row["updated_at"] = now

        snapshot_file(
            MAIL_CSV,
            "user_write",
        )

        snapshot_file(
            PC_CSV,
            "user_write",
        )

        _atomic_write_group_pair(
            mail_fields=mail_fields,
            mail_rows=mail_rows,
            pc_fields=pc_fields,
            pc_rows=pc_rows,
            old_mail_rows=(
                old_mail_rows
            ),
            old_pc_rows=(
                old_pc_rows
            ),
        )


def snooze_group(
    pair_id: str,
    minutes: int = 10,
) -> None:
    if minutes < 1:
        raise ValueError(
            "Erteleme süresi en az 1 dakika olmalı."
        )

    until = (
        dt.datetime.now()
        .replace(second=0, microsecond=0)
        + dt.timedelta(minutes=minutes)
    )

    value = fmt_dt(until)
    now = _now_string()

    with exclusive(MAIL_LOCK), exclusive(PC_LOCK):
        mail_fields, mail_rows = read_csv(
            MAIL_CSV,
            FIELDS,
        )

        pc_fields, pc_rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        mail_fields = ensure_fields(
            mail_fields
        )

        pc_fields = ensure_fields(
            pc_fields
        )

        old_mail_rows = [
            dict(row)
            for row in mail_rows
        ]

        old_pc_rows = [
            dict(row)
            for row in pc_rows
        ]

        found = False

        for rows in (
            mail_rows,
            pc_rows,
        ):
            for row in rows:
                if (
                    row.get("pair_id")
                    or ""
                ).strip() == pair_id:
                    row["enabled"] = "1"
                    row["snooze_until"] = value
                    row["updated_at"] = now
                    found = True

        if not found:
            raise KeyError(pair_id)

        snapshot_file(
            MAIL_CSV,
            "user_write",
        )

        snapshot_file(
            PC_CSV,
            "user_write",
        )

        _atomic_write_group_pair(
            mail_fields=mail_fields,
            mail_rows=mail_rows,
            pc_fields=pc_fields,
            pc_rows=pc_rows,
            old_mail_rows=(
                old_mail_rows
            ),
            old_pc_rows=(
                old_pc_rows
            ),
        )


def load_groups(
    *,
    active_only: bool = False,
) -> List[Dict[str, object]]:
    _, mail_rows = read_csv(
        MAIL_CSV,
        FIELDS,
    )

    _, pc_rows = read_csv(
        PC_CSV,
        FIELDS,
    )

    grouped: Dict[
        str,
        Dict[str, object],
    ] = {}

    for source, rows in (
        ("email", mail_rows),
        ("pc", pc_rows),
    ):
        for row in rows:
            rid = (
                row.get("id")
                or ""
            ).strip()

            pair_id = (
                (
                    row.get("pair_id")
                    or ""
                ).strip()
                or f"{source}-{rid}"
            )

            group = grouped.setdefault(
                pair_id,
                {
                    "pair_id": pair_id,
                    "mail_row": None,
                    "pc_row": None,
                },
            )

            if source == "email":
                group["mail_row"] = row
            else:
                group["pc_row"] = row

    result: List[
        Dict[str, object]
    ] = []

    for pair_id, group in grouped.items():
        mail_row = group.get("mail_row")
        pc_row = group.get("pc_row")

        rows = [
            row
            for row in (
                mail_row,
                pc_row,
            )
            if isinstance(
                row,
                dict,
            )
        ]

        if not rows:
            continue

        enabled = any(
            (
                row.get("enabled")
                or ""
            ).strip() == "1"
            for row in rows
        )

        if (
            active_only
            and not enabled
        ):
            continue

        active_rows = [
            row
            for row in rows
            if (
                row.get("enabled")
                or ""
            ).strip() == "1"
        ]

        source_row = (
            active_rows[0]
            if active_rows
            else rows[0]
        )

        run_values = [
            parse_dt(
                row.get(
                    "next_run",
                    "",
                )
            )
            for row in (
                active_rows
                or rows
            )
        ]

        run_values = [
            value
            for value in run_values
            if value is not None
        ]

        run_at = (
            min(run_values)
            if run_values
            else None
        )

        if (
            mail_row is not None
            and pc_row is not None
        ):
            channel = "both"

        elif mail_row is not None:
            channel = "email"

        else:
            channel = "pc"

        result.append(
            {
                "pair_id": pair_id,
                "channel": channel,
                "enabled": enabled,
                "next_run": run_at,
                "repeat": (
                    source_row.get("repeat")
                    or "once"
                ),
                "subject": (
                    source_row.get("subject")
                    or _localized_core_text(
                        "reminder_fallback"
                    )
                ),
                "body": (
                    source_row.get("body")
                    or ""
                ),
                "category": (
                    source_row.get("category")
                    or "Genel"
                ),
                "anchor_day": (
                    _anchor_from_row(
                        source_row
                    )
                ),
                "created_at": (
                    source_row.get("created_at")
                    or ""
                ),
                "updated_at": (
                    source_row.get("updated_at")
                    or ""
                ),
                "mail_row": mail_row,
                "pc_row": pc_row,
            }
        )

    result.sort(
        key=lambda group: (
            group.get("next_run")
            is None,
            group.get("next_run")
            or dt.datetime.max,
            str(
                group.get("subject")
                or ""
            ).lower(),
        )
    )

    return result


def search_groups(
    query: str = "",
    *,
    channel: Optional[str] = None,
    category: Optional[str] = None,
    include_disabled: bool = True,
) -> List[Dict[str, object]]:
    query = query.strip().casefold()

    result = []

    for group in load_groups():
        if (
            not include_disabled
            and not bool(
                group.get("enabled")
            )
        ):
            continue

        if (
            channel
            and channel != "all"
            and group.get("channel")
            != channel
        ):
            continue

        if (
            category
            and category != "all"
            and group.get("category")
            != category
        ):
            continue

        if query:
            haystack = " ".join(
                [
                    str(
                        group.get("subject")
                        or ""
                    ),
                    str(
                        group.get("body")
                        or ""
                    ),
                    str(
                        group.get("category")
                        or ""
                    ),
                ]
            ).casefold()

            if query not in haystack:
                continue

        result.append(group)

    return result


def duplicate_group(
    pair_id: str,
    *,
    run_at: Optional[dt.datetime] = None,
) -> str:
    groups = {
        str(group["pair_id"]):
        group
        for group in load_groups()
    }

    if pair_id not in groups:
        raise KeyError(pair_id)

    source = groups[pair_id]

    if run_at is None:
        candidate = source.get(
            "next_run"
        )

        if (
            isinstance(
                candidate,
                dt.datetime,
            )
            and candidate
            > dt.datetime.now()
        ):
            run_at = candidate

        else:
            run_at = (
                dt.datetime.now()
                .replace(
                    second=0,
                    microsecond=0,
                )
                + dt.timedelta(
                    minutes=10
                )
            )

    return save_group(
        pair_id=None,
        channel=str(
            source.get("channel")
            or "email"
        ),
        subject=str(
            source.get("subject")
            or _localized_core_text(
                "reminder_fallback"
            )
        )
        + " — "
        + _localized_core_text(
            "duplicate_subject_suffix"
        ),
        body=str(
            source.get("body")
            or ""
        ),
        run_at=run_at,
        repeat=str(
            source.get("repeat")
            or "once"
        ),
        category=str(
            source.get("category")
            or "Genel"
        ),
    )


def append_history(
    *,
    pair_id: str,
    channel: str,
    sent_at: str,
    subject: str,
    body: str,
    category: str = "Genel",
    action: str = "sent",
) -> None:
    with exclusive(HISTORY_LOCK):
        fields, rows = read_csv(
            HISTORY_CSV,
            HISTORY_FIELDS,
        )

        for field in HISTORY_FIELDS:
            if field not in fields:
                fields.append(field)

        rows.append(
            {
                "event_id": uuid.uuid4().hex,
                "pair_id": pair_id,
                "channel": channel,
                "sent_at": sent_at,
                "subject": subject,
                "body": body,
                "category": category,
                "action": action,
            }
        )

        snapshot_file(
            HISTORY_CSV,
            "history",
        )

        atomic_write(
            HISTORY_CSV,
            fields,
            rows,
        )


def load_history() -> List[Dict[str, str]]:
    _, rows = read_csv(
        HISTORY_CSV,
        HISTORY_FIELDS,
    )

    rows.sort(
        key=lambda row:
        parse_dt(
            row.get(
                "sent_at",
                "",
            )
        )
        or dt.datetime.min,
        reverse=True,
    )

    return rows


def compute_next_run(
    after: dt.datetime,
    repeat: str,
    anchor_day: Optional[int] = None,
) -> Optional[dt.datetime]:
    if repeat in {
        "",
        "none",
        "once",
    }:
        return None

    if repeat == "daily":
        return (
            after
            + dt.timedelta(days=1)
        )

    if repeat == "weekly":
        return (
            after
            + dt.timedelta(days=7)
        )

    if repeat == "monthly":
        anchor = (
            anchor_day
            if anchor_day
            and 1 <= anchor_day <= 31
            else after.day
        )

        year = after.year
        month = after.month + 1

        if month == 13:
            month = 1
            year += 1

        last_day = calendar.monthrange(
            year,
            month,
        )[1]

        day = min(
            anchor,
            last_day,
        )

        return after.replace(
            year=year,
            month=month,
            day=day,
        )

    if repeat.startswith(
        "every "
    ):
        spec = repeat[6:].strip()

        try:
            if spec.endswith("m"):
                return (
                    after
                    + dt.timedelta(
                        minutes=int(
                            spec[:-1]
                        )
                    )
                )

            if spec.endswith("h"):
                return (
                    after
                    + dt.timedelta(
                        hours=int(
                            spec[:-1]
                        )
                    )
                )

            if spec.endswith("d"):
                return (
                    after
                    + dt.timedelta(
                        days=int(
                            spec[:-1]
                        )
                    )
                )

        except ValueError:
            return None

    return None


def next_future_run(
    scheduled: dt.datetime,
    repeat: str,
    now: dt.datetime,
    anchor_day: Optional[int] = None,
) -> Optional[dt.datetime]:
    nxt = compute_next_run(
        scheduled,
        repeat,
        anchor_day,
    )

    safety = 0

    while (
        nxt is not None
        and nxt <= now
    ):
        nxt = compute_next_run(
            nxt,
            repeat,
            anchor_day,
        )

        safety += 1

        if safety > 100000:
            raise RuntimeError(
                "Tekrar hesaplama güvenlik sınırını aştı."
            )

    return nxt


def complete_group(
    pair_id: str,
) -> None:
    now = dt.datetime.now().replace(
        second=0,
        microsecond=0,
    )

    with exclusive(MAIL_LOCK), exclusive(PC_LOCK):
        mail_fields, mail_rows = read_csv(
            MAIL_CSV,
            FIELDS,
        )

        pc_fields, pc_rows = read_csv(
            PC_CSV,
            FIELDS,
        )

        mail_fields = ensure_fields(
            mail_fields
        )

        pc_fields = ensure_fields(
            pc_fields
        )

        old_mail_rows = [
            dict(row)
            for row in mail_rows
        ]

        old_pc_rows = [
            dict(row)
            for row in pc_rows
        ]

        found_rows = []

        for rows in (
            mail_rows,
            pc_rows,
        ):
            for row in rows:
                if (
                    row.get("pair_id")
                    or ""
                ).strip() == pair_id:
                    found_rows.append(row)

        if not found_rows:
            raise KeyError(pair_id)

        snapshot_file(
            MAIL_CSV,
            "user_write",
        )

        snapshot_file(
            PC_CSV,
            "user_write",
        )

        for row in found_rows:
            scheduled = parse_dt(
                row.get(
                    "next_run",
                    "",
                )
            )

            repeat = (
                row.get("repeat")
                or "once"
            ).strip()

            anchor = _anchor_from_row(
                row
            )

            nxt = (
                next_future_run(
                    scheduled,
                    repeat,
                    now,
                    anchor,
                )
                if scheduled
                else None
            )

            if nxt is None:
                row["enabled"] = "0"
                row["next_run"] = ""
            else:
                row["enabled"] = "1"
                row["next_run"] = fmt_dt(
                    nxt
                )

            row["snooze_until"] = ""
            row["updated_at"] = (
                _now_string()
            )

        _atomic_write_group_pair(
            mail_fields=mail_fields,
            mail_rows=mail_rows,
            pc_fields=pc_fields,
            pc_rows=pc_rows,
            old_mail_rows=(
                old_mail_rows
            ),
            old_pc_rows=(
                old_pc_rows
            ),
        )

    source = found_rows[0]

    append_history(
        pair_id=pair_id,
        channel="manual",
        sent_at=fmt_dt(now),
        subject=(
            source.get("subject")
            or _localized_core_text(
                "reminder_fallback"
            )
        ),
        body=(
            source.get("body")
            or ""
        ),
        category=(
            source.get("category")
            or "Genel"
        ),
        action="completed",
    )


SETTINGS_STATE_MISSING = "missing"
SETTINGS_STATE_VALID = "valid"
SETTINGS_STATE_CORRUPT_QUARANTINED = (
    "corrupt-quarantined"
)
SETTINGS_STATE_CORRUPT_UNQUARANTINED = (
    "corrupt-unquarantined"
)
SETTINGS_STATE_UNREADABLE = "unreadable"

_LAST_SETTINGS_LOAD_STATE = (
    SETTINGS_STATE_MISSING
)


class SettingsPersistenceError(
    RuntimeError
):
    pass


def settings_load_state() -> str:
    return _LAST_SETTINGS_LOAD_STATE


def settings_quarantine_files() -> List[Path]:
    if not SETTINGS_JSON.parent.exists():
        return []

    return sorted(
        SETTINGS_JSON.parent.glob(
            SETTINGS_JSON.stem
            + ".corrupt-*"
            + SETTINGS_JSON.suffix
        )
    )


def _initial_settings() -> Dict[str, object]:
    # The first-run wizard stores the initial channel in the public
    # profile (settings.json), while the main application stores its
    # preferences in settings_v2.json.  Bridge only matching preference
    # keys so account or SMTP data is never duplicated here.
    result = dict(
        DEFAULT_SETTINGS
    )

    try:
        public_settings = (
            runtime_config
            .load_settings()
        )
    except Exception:
        public_settings = {}

    if isinstance(
        public_settings,
        dict,
    ):
        for key in DEFAULT_SETTINGS:
            if key in public_settings:
                result[key] = (
                    public_settings[key]
                )

    return result


def _read_settings_document(
) -> Tuple[str, Optional[Dict[str, object]]]:
    try:
        with SETTINGS_JSON.open(
            "r",
            encoding="utf-8",
        ) as handle:
            # Harden files created by older releases without rewriting
            # their bytes. fchmod targets the file actually opened.
            os.fchmod(
                handle.fileno(),
                0o600,
            )

            try:
                data = json.load(
                    handle
                )
            except (
                ValueError,
                UnicodeDecodeError,
                RecursionError,
            ):
                return "corrupt", None

    except FileNotFoundError:
        return SETTINGS_STATE_MISSING, None
    except OSError:
        return SETTINGS_STATE_UNREADABLE, None

    if not isinstance(data, dict):
        return "corrupt", None

    return SETTINGS_STATE_VALID, data


def _settings_lock_path() -> Path:
    return SETTINGS_JSON.with_name(
        "."
        + SETTINGS_JSON.name
        + ".lock"
    )


@contextmanager
def _settings_exclusive() -> Iterator[None]:
    SETTINGS_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    lock_path = _settings_lock_path()

    with lock_path.open(
        "a+",
        encoding="utf-8",
    ) as lock_handle:
        os.fchmod(
            lock_handle.fileno(),
            0o600,
        )

        fcntl.flock(
            lock_handle.fileno(),
            fcntl.LOCK_EX,
        )

        try:
            yield

        finally:
            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_UN,
            )


def _fsync_settings_directory() -> None:
    directory_fd = os.open(
        str(
            SETTINGS_JSON.parent
        ),
        os.O_RDONLY
        | getattr(
            os,
            "O_DIRECTORY",
            0,
        ),
    )

    try:
        os.fsync(
            directory_fd
        )
    finally:
        os.close(
            directory_fd
        )


def _quarantine_corrupt_settings_locked(
) -> Optional[Path]:
    state, _ = _read_settings_document()

    if state != "corrupt":
        return None

    stamp = dt.datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    target = SETTINGS_JSON.with_name(
        SETTINGS_JSON.stem
        + ".corrupt-"
        + stamp
        + "-"
        + uuid.uuid4().hex[:8]
        + SETTINGS_JSON.suffix
    )

    os.replace(
        SETTINGS_JSON,
        target,
    )

    with target.open("rb") as handle:
        os.fchmod(
            handle.fileno(),
            0o600,
        )
        os.fsync(
            handle.fileno()
        )

    _fsync_settings_directory()

    return target


def load_settings() -> Dict[str, object]:
    global _LAST_SETTINGS_LOAD_STATE

    result = _initial_settings()
    state, data = _read_settings_document()

    if state == "corrupt":
        try:
            with _settings_exclusive():
                state, data = (
                    _read_settings_document()
                )

                if state == "corrupt":
                    target = (
                        _quarantine_corrupt_settings_locked()
                    )

                    if target is not None:
                        state = (
                            SETTINGS_STATE_CORRUPT_QUARANTINED
                        )

        except OSError:
            state = (
                SETTINGS_STATE_CORRUPT_UNQUARANTINED
            )
            data = None

    _LAST_SETTINGS_LOAD_STATE = state

    if isinstance(data, dict):
        result.update(data)

    return result


def _atomic_write_settings(
    current: Dict[str, object],
) -> None:
    fd, temp_name = tempfile.mkstemp(
        prefix=(
            "."
            + SETTINGS_JSON.name
            + "."
        ),
        suffix=".tmp",
        dir=str(
            SETTINGS_JSON.parent
        ),
        text=True,
    )

    try:
        os.fchmod(
            fd,
            0o600,
        )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    current,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp_name,
            SETTINGS_JSON,
        )

        _fsync_settings_directory()

    finally:
        try:
            os.unlink(
                temp_name
            )
        except FileNotFoundError:
            pass


def save_settings(
    values: Dict[str, object],
) -> None:
    global _LAST_SETTINGS_LOAD_STATE

    with _settings_exclusive():
        current = _initial_settings()
        state, data = _read_settings_document()

        if state == "corrupt":
            try:
                target = (
                    _quarantine_corrupt_settings_locked()
                )
            except OSError as exc:
                _LAST_SETTINGS_LOAD_STATE = (
                    SETTINGS_STATE_CORRUPT_UNQUARANTINED
                )
                raise SettingsPersistenceError(
                    "Corrupt settings could not be quarantined."
                ) from exc

            if target is None:
                # Another writer may have repaired the file while this
                # process waited for the lock; re-read before merging.
                state, data = (
                    _read_settings_document()
                )
            else:
                state = (
                    SETTINGS_STATE_CORRUPT_QUARANTINED
                )
                data = None

        if state == SETTINGS_STATE_UNREADABLE:
            _LAST_SETTINGS_LOAD_STATE = state
            raise SettingsPersistenceError(
                "Settings file is unreadable; refusing to overwrite it."
            )

        if isinstance(data, dict):
            current.update(data)

        current.update(values)

        _atomic_write_settings(
            current
        )

        _LAST_SETTINGS_LOAD_STATE = (
            state
            if state
            == SETTINGS_STATE_CORRUPT_QUARANTINED
            else SETTINGS_STATE_VALID
        )


def is_quiet_time(
    now: Optional[dt.datetime] = None,
    settings: Optional[Dict[str, object]] = None,
) -> bool:
    settings = (
        settings
        or load_settings()
    )

    if not bool(
        settings.get(
            "quiet_hours_enabled",
            False,
        )
    ):
        return False

    now = (
        now
        or dt.datetime.now()
    )

    try:
        start_h, start_m = map(
            int,
            str(
                settings[
                    "quiet_hours_start"
                ]
            ).split(":"),
        )

        end_h, end_m = map(
            int,
            str(
                settings[
                    "quiet_hours_end"
                ]
            ).split(":"),
        )

    except Exception:
        return False

    current = (
        now.hour * 60
        + now.minute
    )

    start = (
        start_h * 60
        + start_m
    )

    end = (
        end_h * 60
        + end_m
    )

    if start == end:
        return True

    if start < end:
        return (
            start
            <= current
            < end
        )

    return (
        current >= start
        or current < end
    )
