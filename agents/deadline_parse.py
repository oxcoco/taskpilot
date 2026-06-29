"""Shared deadline parsing and normalization for TaskPilot."""

from __future__ import annotations

import datetime
import re

_WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DEADLINE_SUFFIX_RE = re.compile(
    r"^(?P<title>.+?)\s+(?:by|due(?:\s+on)?|before)\s+(?P<deadline>.+)$",
    re.IGNORECASE,
)
_TIME_SUFFIX_RE = re.compile(
    r"\s+at\s+\d{1,2}(:\d{2})?\s*(am|pm)?$",
    re.IGNORECASE,
)


def _weekday_date(day_name: str, today: datetime.date, *, force_next: bool = False) -> datetime.date | None:
    key = day_name.lower().strip()
    if key not in _WEEKDAYS:
        return None
    target = _WEEKDAYS[key]
    days_ahead = (target - today.weekday()) % 7
    if force_next and days_ahead == 0:
        days_ahead = 7
    return today + datetime.timedelta(days=days_ahead)


def normalize_deadline(deadline: str | None) -> str | None:
    """Convert natural-language or ISO deadline strings to YYYY-MM-DD when possible."""
    if not deadline:
        return None

    raw = deadline.strip()
    raw = _TIME_SUFFIX_RE.sub("", raw).strip()
    if not raw:
        return None

    today = datetime.date.today()
    lower = raw.lower()

    if _ISO_RE.match(raw):
        return raw

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d %Y", "%B %d", "%b %d %Y", "%b %d"):
        try:
            parsed = datetime.datetime.strptime(raw, fmt).date()
            if fmt in ("%B %d", "%b %d") and parsed.year == 1900:
                parsed = parsed.replace(year=today.year)
                if parsed < today:
                    parsed = parsed.replace(year=today.year + 1)
            return parsed.isoformat()
        except ValueError:
            pass

    if lower == "today":
        return today.isoformat()
    if lower == "tomorrow":
        return (today + datetime.timedelta(days=1)).isoformat()

    if lower.startswith("next "):
        day = _weekday_date(lower[5:].strip(), today, force_next=True)
        if day:
            return day.isoformat()

    day = _weekday_date(lower, today)
    if day:
        return day.isoformat()

    return raw


def parse_title_and_deadline(fragment: str) -> tuple[str, str | None]:
    """Split a task phrase into title and optional normalized deadline."""
    text = fragment.strip()
    text = _TIME_SUFFIX_RE.sub("", text).strip()

    match = _DEADLINE_SUFFIX_RE.match(text)
    if match:
        title = match.group("title").strip()
        raw_deadline = match.group("deadline").strip()
        return title, normalize_deadline(raw_deadline)

    return text, None
