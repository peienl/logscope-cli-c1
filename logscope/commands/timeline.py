"""`logscope timeline` — ERROR-level counts per fixed time bucket, as a bar chart."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .. import output as out
from ..parsing import ERROR_LEVELS, ParseStats, iter_entries
from ..timeutil import floor_to_bucket, humanize_duration


def run(
    file: str,
    bucket: timedelta,
    fmt: str = "text",
    output: Optional[str] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Dict[str, Any]:
    stats = ParseStats()
    bucket_counts: Dict[datetime, int] = {}

    for entry in iter_entries(file, encoding=encoding, errors=errors, stats=stats):
        if entry.level not in ERROR_LEVELS:
            continue
        bucket_start = floor_to_bucket(entry.timestamp, bucket)
        bucket_counts[bucket_start] = bucket_counts.get(bucket_start, 0) + 1

    buckets = _fill_gaps(bucket_counts, bucket)

    data: Dict[str, Any] = {
        "file": file,
        "bucket_size": humanize_duration(bucket),
        "total_lines": stats.total_lines,
        "malformed_lines": stats.malformed_lines,
        "buckets": buckets,
    }

    target_path = out.resolve_output_path(file, "timeline", fmt, output)

    if fmt == "json":
        content = _render_json(data)
    elif fmt == "md":
        content = _render_md(data)
    else:
        content = _render_text(data)

    out.write_output(content, target_path, fmt)
    return data


def _fill_gaps(
    bucket_counts: Dict[datetime, int], bucket: timedelta
) -> List[Tuple[datetime, int]]:
    """Fill zero-count buckets between the first and last observed bucket."""
    if not bucket_counts:
        return []
    start = min(bucket_counts)
    end = max(bucket_counts)
    buckets: List[Tuple[datetime, int]] = []
    current = start
    while current <= end:
        buckets.append((current, bucket_counts.get(current, 0)))
        current += bucket
    return buckets


def _label(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M")


def _render_text(data: Dict[str, Any]) -> str:
    lines = [
        f"File: {data['file']}",
        f"Bucket size: {data['bucket_size']}",
        f"Total lines read: {data['total_lines']}",
        f"Malformed lines skipped: {data['malformed_lines']}",
        "",
    ]
    if not data["buckets"]:
        lines.append("No ERROR-level entries found.")
        return "\n".join(lines)

    labels = [_label(ts) for ts, _ in data["buckets"]]
    values = [count for _, count in data["buckets"]]
    lines.append("Error counts per bucket:")
    lines.append(out.bar_chart(labels, values))
    return "\n".join(lines)


def _render_json(data: Dict[str, Any]) -> str:
    payload = {
        "file": data["file"],
        "bucket_size": data["bucket_size"],
        "total_lines": data["total_lines"],
        "malformed_lines": data["malformed_lines"],
        "buckets": [
            {"start": out.format_timestamp(ts), "error_count": count}
            for ts, count in data["buckets"]
        ],
    }
    return out.dump_json(payload)


def _render_md(data: Dict[str, Any]) -> str:
    meta = out.md_bullet_list(
        [
            f"**File:** {data['file']}",
            f"**Bucket size:** {data['bucket_size']}",
            f"**Total lines read:** {data['total_lines']}",
            f"**Malformed lines skipped:** {data['malformed_lines']}",
        ]
    )
    sections = [("Overview", meta)]

    if not data["buckets"]:
        sections.append(("Timeline", "_No ERROR-level entries found._"))
    else:
        labels = [_label(ts) for ts, _ in data["buckets"]]
        values = [count for _, count in data["buckets"]]
        chart = out.bar_chart(labels, values)
        sections.append(("Timeline (error count per bucket)", out.md_code_block(chart)))
        table_rows = [[label, value] for label, value in zip(labels, values)]
        sections.append(
            ("Bucket Counts", out.md_table(["Bucket Start", "Error Count"], table_rows))
        )

    return out.md_document(f"Timeline Report — {data['file']}", sections)
