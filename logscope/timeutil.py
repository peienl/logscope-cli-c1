"""Timestamp and duration parsing helpers."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S,%f",
    "%Y-%m-%dT%H:%M:%S",
)

_USER_DATETIME_FORMATS = _TIMESTAMP_FORMATS + (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
)

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.IGNORECASE)
_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Parse a log-line timestamp. Returns None if it matches no known format."""
    raw = raw.strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_user_datetime(raw: str) -> datetime:
    """Parse a user-supplied --since/--until value. Raises ValueError on failure."""
    raw = raw.strip()
    for fmt in _USER_DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Could not parse datetime {raw!r}. Expected formats like "
        "'2026-10-01 09:00:00', '2026-10-01 09:00' or '2026-10-01'."
    )


def parse_duration(raw: str) -> timedelta:
    """Parse a bucket size like '15m', '30s', '2h', '1d'."""
    match = _DURATION_RE.match(raw)
    if not match:
        raise ValueError(
            f"Invalid bucket size {raw!r}. Expected <number><unit> with unit in "
            "s/m/h/d, e.g. '15m'."
        )
    value, unit = match.groups()
    seconds = int(value) * _DURATION_UNITS[unit.lower()]
    if seconds <= 0:
        raise ValueError("Bucket size must be greater than zero.")
    return timedelta(seconds=seconds)


def humanize_duration(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if total % size == 0 and total >= size:
            return f"{total // size}{unit}"
    return f"{total}s"


def floor_to_bucket(ts: datetime, bucket: timedelta) -> datetime:
    """Floor a timestamp down to the start of its bucket window.

    Bucketing is anchored at midnight of the timestamp's own day so that
    bucket boundaries are stable and human-readable (e.g. 15m buckets land
    on :00/:15/:30/:45).
    """
    day_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = ts - day_start
    bucket_seconds = bucket.total_seconds()
    floored_seconds = (elapsed.total_seconds() // bucket_seconds) * bucket_seconds
    return day_start + timedelta(seconds=floored_seconds)
