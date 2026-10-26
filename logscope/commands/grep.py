"""`logscope grep` — stream matching log entries filtered by level and/or time range.

Unlike `summary`/`timeline` (whose in-memory aggregates are bounded by a
small number of distinct values), `grep` can match an unbounded number of
lines in a 100 MB+ log. So its output is written directly to the sink
(stdout or the target file) as matches are found, never buffered into a
list first.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import IO, List, Optional, Set, Tuple

from .. import output as out
from ..parsing import LogEntry, ParseStats, iter_entries


def run(
    file: str,
    levels: Optional[Set[str]] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    fmt: str = "text",
    output: Optional[str] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> int:
    stats = ParseStats()
    target_path = out.resolve_output_path(file, "grep", fmt, output)
    sink, should_close = _open_sink(target_path)

    try:
        match_count = _stream(
            sink, fmt, file, levels, since, until, encoding, errors, stats
        )
    finally:
        if should_close:
            sink.close()

    out.print_confirmation(target_path, fmt)
    return match_count


def _open_sink(target_path: Optional[str]) -> Tuple[IO[str], bool]:
    if target_path is None:
        return sys.stdout, False
    return open(target_path, "w", encoding="utf-8"), True


def _matches(
    entry: LogEntry,
    levels: Optional[Set[str]],
    since: Optional[datetime],
    until: Optional[datetime],
) -> bool:
    if levels and entry.level not in levels:
        return False
    if since is not None and entry.timestamp < since:
        return False
    if until is not None and entry.timestamp > until:
        return False
    return True


def _json_entry(entry: LogEntry) -> str:
    obj = {
        "timestamp": out.format_timestamp(entry.timestamp),
        "level": entry.level,
        "message": entry.message,
        "text": entry.full_text,
    }
    return json.dumps(obj)


def _stream(
    sink: IO[str],
    fmt: str,
    file: str,
    levels: Optional[Set[str]],
    since: Optional[datetime],
    until: Optional[datetime],
    encoding: str,
    errors: str,
    stats: ParseStats,
) -> int:
    match_count = 0
    is_first_match = True
    level_list: Optional[List[str]] = sorted(levels) if levels else None

    if fmt == "json":
        sink.write("{\n")
        sink.write(f"  \"file\": {json.dumps(file)},\n")
        sink.write(f"  \"levels\": {json.dumps(level_list)},\n")
        sink.write(f"  \"since\": {json.dumps(out.format_timestamp(since))},\n")
        sink.write(f"  \"until\": {json.dumps(out.format_timestamp(until))},\n")
        sink.write("  \"matches\": [\n")
    elif fmt == "md":
        sink.write(out.md_heading(f"Grep Report — {file}", level=1) + "\n\n")
        sink.write(out.md_heading("Overview", level=2) + "\n")
        sink.write(
            out.md_bullet_list(
                [
                    f"**Levels filter:** {', '.join(level_list) if level_list else 'any'}",
                    f"**Since:** {out.format_timestamp(since) or 'N/A'}",
                    f"**Until:** {out.format_timestamp(until) or 'N/A'}",
                ]
            )
            + "\n\n"
        )
        sink.write(out.md_heading("Matches", level=2) + "\n\n")

    for entry in iter_entries(file, encoding=encoding, errors=errors, stats=stats):
        if not _matches(entry, levels, since, until):
            continue
        match_count += 1

        if fmt == "json":
            if not is_first_match:
                sink.write(",\n")
            sink.write("    " + _json_entry(entry))
            is_first_match = False
        elif fmt == "md":
            sink.write(f"**{out.format_timestamp(entry.timestamp)} [{entry.level}]**\n\n")
            sink.write(out.md_code_block(entry.full_text) + "\n\n")
        else:
            sink.write(entry.full_text + "\n")

    if fmt == "json":
        sink.write("\n  ],\n")
        sink.write(f"  \"match_count\": {match_count},\n")
        sink.write(f"  \"malformed_lines\": {stats.malformed_lines},\n")
        sink.write(f"  \"total_lines\": {stats.total_lines}\n")
        sink.write("}\n")
    elif fmt == "md":
        if match_count == 0:
            sink.write("_No matching entries found._\n\n")
        sink.write(out.md_heading("Stats", level=2) + "\n")
        sink.write(
            out.md_bullet_list(
                [
                    f"**Matches:** {match_count}",
                    f"**Malformed lines skipped:** {stats.malformed_lines}",
                    f"**Total lines read:** {stats.total_lines}",
                ]
            )
            + "\n"
        )
    else:
        sink.write(f"\nMatches: {match_count}\n")
        sink.write(f"Malformed lines skipped: {stats.malformed_lines}\n")

    return match_count
