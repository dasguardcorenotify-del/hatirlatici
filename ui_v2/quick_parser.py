#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Optional


WEEKDAYS = {
    "pazartesi": 0,
    "salı": 1,
    "sali": 1,
    "çarşamba": 2,
    "carsamba": 2,
    "perşembe": 3,
    "persembe": 3,
    "cuma": 4,
    "cumartesi": 5,
    "pazar": 6,
}


LOCALIZED_WEEKDAYS = {
    # English
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    # German
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
    # Spanish
    "lunes": 0,
    "martes": 1,
    "miércoles": 2,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sábado": 5,
    "sabado": 5,
    "domingo": 6,
    # Russian (nominative and common accusative forms)
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "среду": 2,
    "четверг": 3,
    "пятница": 4,
    "пятницу": 4,
    "суббота": 5,
    "субботу": 5,
    "воскресенье": 6,
}


@dataclass(frozen=True)
class QuickResult:
    subject: str
    run_at: dt.datetime
    repeat: str = "once"


def _clean_subject(value: str) -> str:
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip(" ,.-")

    return value


def _parse_clock(
    hour: str,
    minute: Optional[str],
) -> tuple[int, int]:
    h = int(hour)
    m = int(minute or "0")

    if not (
        0 <= h <= 23
        and 0 <= m <= 59
    ):
        raise ValueError(
            "Geçersiz saat."
        )

    return h, m


def _next_weekday(
    now: dt.datetime,
    weekday: int,
    hour: int,
    minute: int,
) -> dt.datetime:
    days = (
        weekday
        - now.weekday()
    ) % 7

    candidate = (
        now
        + dt.timedelta(days=days)
    ).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate <= now:
        candidate += dt.timedelta(
            days=7
        )

    return candidate


def _subject_around(prefix: str, suffix: Optional[str] = None) -> str:
    """Join a subject split by a language's mid-sentence time phrase."""

    return _clean_subject(
        " ".join(
            part
            for part in (prefix, suffix or "")
            if part and part.strip()
        )
    )


def _localized_relative(original: str, now: dt.datetime) -> Optional[QuickResult]:
    patterns = (
        # English: "Check the tea in 30 minutes" / "In 2 hours call Alex"
        (r"^\s*(.+?)\s+in\s+(\d+)\s+(minutes?|mins?)\s*$", 1, 2, "minutes"),
        (r"^\s*in\s+(\d+)\s+(minutes?|mins?)\s+(.+?)\s*$", 3, 1, "minutes"),
        (r"^\s*(.+?)\s+in\s+(\d+)\s+(hours?|hrs?)\s*$", 1, 2, "hours"),
        (r"^\s*in\s+(\d+)\s+(hours?|hrs?)\s+(.+?)\s*$", 3, 1, "hours"),
        (r"^\s*(.+?)\s+in\s+(\d+)\s+days?\s*$", 1, 2, "days"),
        (r"^\s*in\s+(\d+)\s+days?\s+(.+?)\s*$", 3, 1, "days"),
        # German: "In 30 Minuten nach dem Tee sehen"
        (r"^\s*in\s+(\d+)\s+minuten?\s+(.+?)\s*$", 2, 1, "minutes"),
        (r"^\s*(.+?)\s+in\s+(\d+)\s+minuten?\s*$", 1, 2, "minutes"),
        (r"^\s*in\s+(\d+)\s+stunden?\s+(.+?)\s*$", 2, 1, "hours"),
        (r"^\s*(.+?)\s+in\s+(\d+)\s+stunden?\s*$", 1, 2, "hours"),
        (r"^\s*in\s+(\d+)\s+tagen?\s+(.+?)\s*$", 2, 1, "days"),
        (r"^\s*(.+?)\s+in\s+(\d+)\s+tagen?\s*$", 1, 2, "days"),
        # Spanish: "Comprobar el té dentro de 30 minutos"
        (r"^\s*(.+?)\s+dentro\s+de\s+(\d+)\s+minutos?\s*$", 1, 2, "minutes"),
        (r"^\s*dentro\s+de\s+(\d+)\s+minutos?\s+(.+?)\s*$", 2, 1, "minutes"),
        (r"^\s*(.+?)\s+dentro\s+de\s+(\d+)\s+horas?\s*$", 1, 2, "hours"),
        (r"^\s*dentro\s+de\s+(\d+)\s+horas?\s+(.+?)\s*$", 2, 1, "hours"),
        (r"^\s*(.+?)\s+dentro\s+de\s+(\d+)\s+d[ií]as?\s*$", 1, 2, "days"),
        # Russian: "Проверить чай через 30 минут"
        (r"^\s*(.+?)\s+через\s+(\d+)\s+минут(?:у|ы)?\s*$", 1, 2, "minutes"),
        (r"^\s*через\s+(\d+)\s+минут(?:у|ы)?\s+(.+?)\s*$", 2, 1, "minutes"),
        (r"^\s*(.+?)\s+через\s+(\d+)\s+час(?:а|ов)?\s*$", 1, 2, "hours"),
        (r"^\s*через\s+(\d+)\s+час(?:а|ов)?\s+(.+?)\s*$", 2, 1, "hours"),
        (r"^\s*(.+?)\s+через\s+(\d+)\s+(?:день|дня|дней)\s*$", 1, 2, "days"),
    )

    for pattern, subject_group, number_group, unit in patterns:
        match = re.match(pattern, original, flags=re.I)
        if not match:
            continue
        amount = int(match.group(number_group))
        if amount < 1:
            return None
        return QuickResult(
            _clean_subject(match.group(subject_group)),
            now + dt.timedelta(**{unit: amount}),
        )

    return None


def _localized_named_day(original: str, now: dt.datetime) -> Optional[QuickResult]:
    """Parse the idiomatic word order used by the four translated UIs."""

    clock = r"(\d{1,2})(?::(\d{2}))?"
    day_patterns = (
        # prefix, time word, suffix; the subject can surround the time phrase
        (rf"^\s*(.+?)\s+tomorrow\s+(?:at\s+)?{clock}\s*$", 1, None, 2, 3, 1),
        (rf"^\s*tomorrow\s+(?:at\s+)?{clock}\s+(.+?)\s*$", 3, None, 1, 2, 1),
        (rf"^\s*(.+?)\s+morgen\s+um\s+{clock}(?:\s+(.+?))?\s*$", 1, 4, 2, 3, 1),
        (rf"^\s*morgen\s+um\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 1),
        (rf"^\s*(.+?)\s+ma[ñn]ana\s+a\s+las?\s+{clock}\s*$", 1, None, 2, 3, 1),
        (rf"^\s*ma[ñn]ana\s+a\s+las?\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 1),
        (rf"^\s*(.+?)\s+завтра\s+в\s+{clock}\s*$", 1, None, 2, 3, 1),
        (rf"^\s*завтра\s+в\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 1),
        (rf"^\s*(.+?)\s+today\s+(?:at\s+)?{clock}\s*$", 1, None, 2, 3, 0),
        (rf"^\s*today\s+(?:at\s+)?{clock}\s+(.+?)\s*$", 3, None, 1, 2, 0),
        (rf"^\s*(.+?)\s+heute\s+um\s+{clock}(?:\s+(.+?))?\s*$", 1, 4, 2, 3, 0),
        (rf"^\s*heute\s+um\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 0),
        (rf"^\s*(.+?)\s+hoy\s+a\s+las?\s+{clock}\s*$", 1, None, 2, 3, 0),
        (rf"^\s*hoy\s+a\s+las?\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 0),
        (rf"^\s*(.+?)\s+сегодня\s+в\s+{clock}\s*$", 1, None, 2, 3, 0),
        (rf"^\s*сегодня\s+в\s+{clock}\s+(.+?)\s*$", 3, None, 1, 2, 0),
    )

    for pattern, prefix_group, suffix_group, hour_group, minute_group, days in day_patterns:
        match = re.match(pattern, original, flags=re.I)
        if not match:
            continue
        hour, minute = _parse_clock(
            match.group(hour_group),
            match.group(minute_group),
        )
        run_at = (now + dt.timedelta(days=days)).replace(hour=hour, minute=minute)
        if run_at <= now:
            return None
        return QuickResult(
            _subject_around(
                match.group(prefix_group),
                match.group(suffix_group) if suffix_group else None,
            ),
            run_at,
        )

    return None


def _localized_recurrence(original: str, now: dt.datetime) -> Optional[QuickResult]:
    clock = r"(\d{1,2})(?::(\d{2}))?"
    daily_patterns = (
        rf"^\s*every\s+day\s+(?:at\s+)?{clock}\s+(.+?)\s*$",
        rf"^\s*jeden\s+tag\s+um\s+{clock}\s+(.+?)\s*$",
        rf"^\s*cada\s+d[ií]a\s+a\s+las?\s+{clock}\s+(.+?)\s*$",
        rf"^\s*каждый\s+день\s+в\s+{clock}\s+(.+?)\s*$",
    )
    for pattern in daily_patterns:
        match = re.match(pattern, original, flags=re.I)
        if not match:
            continue
        hour, minute = _parse_clock(match.group(1), match.group(2))
        run_at = now.replace(hour=hour, minute=minute)
        if run_at <= now:
            run_at += dt.timedelta(days=1)
        return QuickResult(_clean_subject(match.group(3)), run_at, "daily")

    weekly_patterns = (
        rf"^\s*every\s+([\wáéíóúäöüßё]+)\s+(?:at\s+)?{clock}\s+(.+?)\s*$",
        rf"^\s*jeden?\s+([\wáéíóúäöüßё]+)\s+um\s+{clock}\s+(.+?)\s*$",
        rf"^\s*cada\s+([\wáéíóúäöüßё]+)\s+a\s+las?\s+{clock}\s+(.+?)\s*$",
        rf"^\s*кажд(?:ый|ую|ое)\s+([\wáéíóúäöüßё]+)\s+в\s+{clock}\s+(.+?)\s*$",
    )
    for pattern in weekly_patterns:
        match = re.match(pattern, original, flags=re.I)
        if not match:
            continue
        weekday = LOCALIZED_WEEKDAYS.get(match.group(1).casefold())
        if weekday is None:
            continue
        hour, minute = _parse_clock(match.group(2), match.group(3))
        return QuickResult(
            _clean_subject(match.group(4)),
            _next_weekday(now, weekday, hour, minute),
            "weekly",
        )

    return None


def _parse_quick_unsafe(
    text: str,
    *,
    now: Optional[dt.datetime] = None,
) -> Optional[QuickResult]:
    now = (
        now
        or dt.datetime.now()
    ).replace(
        second=0,
        microsecond=0,
    )

    original = text.strip()

    if not original:
        return None

    # 3 gün sonra aboneliği iptal et
    match = re.match(
        r"^\s*(\d+)\s*g[üu]n\s+sonra\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        days = int(match.group(1))

        if days < 1:
            return None

        return QuickResult(
            _clean_subject(match.group(2)),
            now + dt.timedelta(days=days),
        )

    # gelecek pazartesi 10:00 toplantıya hazırlan
    match = re.match(
        r"^\s*gelecek\s+([a-zçğıöşü]+)\s+"
        r"(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        day_name = match.group(1).casefold()

        if day_name in WEEKDAYS:
            h, m = _parse_clock(
                match.group(2),
                match.group(3),
            )

            candidate = _next_weekday(
                now,
                WEEKDAYS[day_name],
                h,
                m,
            )

            # "gelecek X" en az bir sonraki haftayı ifade etsin.
            if (
                candidate.date() - now.date()
            ).days < 7:
                candidate += dt.timedelta(days=7)

            return QuickResult(
                _clean_subject(match.group(4)),
                candidate,
            )

    # ayın 1'inde saat 09:00 kirayı öde
    match = re.match(
        r"^\s*ay[ıi]n\s+(\d{1,2})"
        r"['’]?(?:inde|ında|unda|ünde)\s+"
        r"(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        import calendar

        requested_day = int(match.group(1))
        h, m = _parse_clock(
            match.group(2),
            match.group(3),
        )

        if not 1 <= requested_day <= 31:
            return None

        year = now.year
        month = now.month

        def make_candidate(y, mo):
            last = calendar.monthrange(y, mo)[1]
            return dt.datetime(
                y,
                mo,
                min(requested_day, last),
                h,
                m,
            )

        candidate = make_candidate(
            year,
            month,
        )

        if candidate <= now:
            month += 1

            if month == 13:
                month = 1
                year += 1

            candidate = make_candidate(
                year,
                month,
            )

        return QuickResult(
            _clean_subject(match.group(4)),
            candidate,
        )

    # 30 dakika sonra çayı kontrol et
    match = re.match(
        r"^\s*(\d+)\s*(dakika|dk)\s+sonra\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        minutes = int(
            match.group(1)
        )

        if minutes < 1:
            return None

        return QuickResult(
            _clean_subject(
                match.group(3)
            ),
            now
            + dt.timedelta(
                minutes=minutes
            ),
        )

    # 2 saat sonra bankayı ara
    match = re.match(
        r"^\s*(\d+)\s*saat\s+sonra\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        hours = int(
            match.group(1)
        )

        if hours < 1:
            return None

        return QuickResult(
            _clean_subject(
                match.group(2)
            ),
            now
            + dt.timedelta(
                hours=hours
            ),
        )

    # yarın saat 9'da Ahmet'i ara
    # yarın 09:30 Ahmet'i ara
    match = re.match(
        r"^\s*yar[ıi]n\s+(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        h, m = _parse_clock(
            match.group(1),
            match.group(2),
        )

        run_at = (
            now
            + dt.timedelta(days=1)
        ).replace(
            hour=h,
            minute=m,
        )

        return QuickResult(
            _clean_subject(
                match.group(3)
            ),
            run_at,
        )

    # bugün 18:30 faturayı öde
    match = re.match(
        r"^\s*bug[üu]n\s+(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        h, m = _parse_clock(
            match.group(1),
            match.group(2),
        )

        run_at = now.replace(
            hour=h,
            minute=m,
        )

        if run_at <= now:
            return None

        return QuickResult(
            _clean_subject(
                match.group(3)
            ),
            run_at,
        )

    # her cuma 14:00 raporu gönder
    match = re.match(
        r"^\s*her\s+([a-zçğıöşü]+)\s+"
        r"(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        day_name = (
            match.group(1)
            .casefold()
        )

        if day_name in WEEKDAYS:
            h, m = _parse_clock(
                match.group(2),
                match.group(3),
            )

            run_at = _next_weekday(
                now,
                WEEKDAYS[day_name],
                h,
                m,
            )

            return QuickResult(
                _clean_subject(
                    match.group(4)
                ),
                run_at,
                "weekly",
            )

    # cuma 14:00 doktoru ara
    match = re.match(
        r"^\s*([a-zçğıöşü]+)\s+"
        r"(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        day_name = (
            match.group(1)
            .casefold()
        )

        if day_name in WEEKDAYS:
            h, m = _parse_clock(
                match.group(2),
                match.group(3),
            )

            return QuickResult(
                _clean_subject(
                    match.group(4)
                ),
                _next_weekday(
                    now,
                    WEEKDAYS[
                        day_name
                    ],
                    h,
                    m,
                ),
            )

    # her gün 08:30 ilacı al
    match = re.match(
        r"^\s*her\s+g[üu]n\s+"
        r"(?:saat\s+)?"
        r"(\d{1,2})(?::(\d{2}))?"
        r"(?:['’]?(?:da|de|ta|te))?\s+(.+)$",
        original,
        flags=re.I,
    )

    if match:
        h, m = _parse_clock(
            match.group(1),
            match.group(2),
        )

        run_at = now.replace(
            hour=h,
            minute=m,
        )

        if run_at <= now:
            run_at += dt.timedelta(
                days=1
            )

        return QuickResult(
            _clean_subject(
                match.group(3)
            ),
            run_at,
            "daily",
        )

    for localized_parser in (
        _localized_relative,
        _localized_named_day,
        _localized_recurrence,
    ):
        result = localized_parser(original, now)
        if result is not None:
            return result

    return None


def parse_quick(
    text: str,
    *,
    now: Optional[dt.datetime] = None,
) -> Optional[QuickResult]:
    """Parse a quick phrase without leaking input errors into the UI."""

    try:
        result = _parse_quick_unsafe(
            text,
            now=now,
        )

        if (
            result is not None
            and not result.subject
        ):
            return None

        return result
    except (
        ValueError,
        OverflowError,
    ):
        return None
