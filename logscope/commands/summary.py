"""`logscope summary` — level counts, top error messages, first/last timestamp."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Optional

from .. import output as out
from ..parsing import ERROR_LEVELS, ParseStats, iter_entries

TOP_N_ERRORS = 5


def run(
    file: str,
    fmt: str = "text",
    output: Optional[str] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Dict[str, Any]:
    stats = ParseStats()
    counts_by_level: Counter = Counter()
    error_messages: Counter = Counter()
    first_ts = None
    last_ts = None

    for entry in iter_entries(file, encoding=encoding, errors=errors, stats=stats):
        counts_by_level[entry.level] += 1
        if entry.level in ERROR_LEVELS:
            error_messages[entry.message] += 1
        if first_ts is None or entry.timestamp < first_ts:
            first_ts = entry.timestamp
        if last_ts is None or entry.timestamp > last_ts:
            last_ts = entry.timestamp

    top_errors = error_messages.most_common(TOP_N_ERRORS)

    data: Dict[str, Any] = {
        "file": file,
        "total_lines": stats.total_lines,
        "malformed_lines": stats.malformed_lines,
        "counts_by_level": dict(sorted(counts_by_level.items())),
        "top_errors": [{"message": msg, "count": cnt} for msg, cnt in top_errors],
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
    }

    target_path = out.resolve_output_path(file, "summary", fmt, output)

    if fmt == "json":
        content = out.dump_json(data)
    elif fmt == "md":
        content = _render_md(data)
    else:
        content = _render_text(data)

    out.write_output(content, target_path, fmt)
    return data


def _render_text(data: Dict[str, Any]) -> str:
    lines = [
        f"File: {data['file']}",
        f"Total lines read: {data['total_lines']}",
        f"Malformed lines skipped: {data['malformed_lines']}",
        "",
        "Counts by level:",
    ]
    if data["counts_by_level"]:
        lines.append(out.text_table(["Level", "Count"], list(data["counts_by_level"].items())))
    else:
        lines.append("  (no entries found)")

    lines.append("")
    lines.append(f"Top {TOP_N_ERRORS} error messages:")
    if data["top_errors"]:
        rows = [[e["message"], e["count"]] for e in data["top_errors"]]
        lines.append(out.text_table(["Message", "Count"], rows))
    else:
        lines.append("  (no error-level entries found)")

    lines.append("")
    lines.append(f"First timestamp: {out.format_timestamp(data['first_timestamp']) or 'N/A'}")
    lines.append(f"Last timestamp:  {out.format_timestamp(data['last_timestamp']) or 'N/A'}")
    return "\n".join(lines)


def _render_md(data: Dict[str, Any]) -> str:
    meta = out.md_bullet_list(
        [
            f"**File:** {data['file']}",
            f"**Total lines read:** {data['total_lines']}",
            f"**Malformed lines skipped:** {data['malformed_lines']}",
            f"**First timestamp:** {out.format_timestamp(data['first_timestamp']) or 'N/A'}",
            f"**Last timestamp:** {out.format_timestamp(data['last_timestamp']) or 'N/A'}",
        ]
    )
    sections = [("Overview", meta)]

    if data["counts_by_level"]:
        body = out.md_table(["Level", "Count"], list(data["counts_by_level"].items()))
    else:
        body = "_No entries found._"
    sections.append(("Counts by Level", body))

    if data["top_errors"]:
        rows = [[e["message"], e["count"]] for e in data["top_errors"]]
        body = out.md_table(["Message", "Count"], rows)
    else:
        body = "_No error-level entries found._"
    sections.append((f"Top {TOP_N_ERRORS} Error Messages", body))

    return out.md_document(f"Summary Report — {data['file']}", sections)
