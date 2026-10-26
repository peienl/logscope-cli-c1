"""Streaming log-line parser.

Reads a log file line-by-line (never loading it fully into memory) and
yields LogEntry objects, grouping continuation lines (e.g. stack traces)
into the preceding entry. Malformed lines are counted, never raised.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, List, Optional

from .timeutil import parse_timestamp

ERROR_LEVELS = frozenset({"ERROR", "FATAL", "CRITICAL"})
KNOWN_LEVELS = frozenset({"TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "CRITICAL"})

_TIMESTAMP_PATTERN = r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"
_LEVEL_PATTERN = r"(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)"
_HEADER_RE = re.compile(
    rf"^({_TIMESTAMP_PATTERN})\s+{_LEVEL_PATTERN}\b[:\-\|]?\s*(.*)$",
    re.IGNORECASE,
)


def normalize_level(raw: str) -> str:
    """Normalize a user- or log-supplied level name (e.g. 'WARNING' -> 'WARN')."""
    level = raw.upper()
    return "WARN" if level == "WARNING" else level


@dataclass
class ParseStats:
    total_lines: int = 0
    malformed_lines: int = 0


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    message: str
    lines: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(self.lines)


def iter_entries(
    path: str,
    encoding: str = "utf-8",
    errors: str = "replace",
    stats: Optional[ParseStats] = None,
) -> Iterator[LogEntry]:
    """Stream `path` and yield one LogEntry per log record.

    - Blank/whitespace-only lines are skipped silently.
    - Lines matching the header pattern start a new entry.
    - Non-header lines are appended as continuations of the current entry,
      unless there is no current entry, in which case they are malformed.
    - A header-shaped line with an unparsable timestamp is malformed.
    """
    if stats is None:
        stats = ParseStats()

    current: Optional[LogEntry] = None
    with open(path, "r", encoding=encoding, errors=errors) as handle:
        for raw_line in handle:
            stats.total_lines += 1
            line = raw_line.rstrip("\r\n")
            if not line.strip():
                continue

            match = _HEADER_RE.match(line)
            if match:
                ts_raw, level_raw, rest = match.groups()
                timestamp = parse_timestamp(ts_raw)
                if timestamp is None:
                    if current is not None:
                        yield current
                        current = None
                    stats.malformed_lines += 1
                    continue
                if current is not None:
                    yield current
                current = LogEntry(
                    timestamp=timestamp,
                    level=normalize_level(level_raw),
                    message=rest,
                    lines=[line],
                )
            elif current is not None:
                current.lines.append(line)
            else:
                stats.malformed_lines += 1

    if current is not None:
        yield current
